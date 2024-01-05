import re
import scrapers
from decimal import Decimal, ROUND_UP


our_margin = Decimal('1.3')


def find_product_details(vendor_and_sku):
    [vendor, sku] = vendor_and_sku.split(':', 2)

    if vendor == 'ah':
        return scrapers.ah_get_by_sku(sku)

    raise Exception(f'unknown vendor: {vendor}')


def update_product_pricings(src):
    lines = src.split('\n')

    find_updatable = re.compile(r'#\s*(?P<sku>\S+)\s+(?P<units>\d+)x$')
    find_aliases = re.compile(r'^(?P<aliases>\S+)')

    lines_out = []

    for line in lines:
        m = find_updatable.search(line)
        if not m:
            lines_out.append(line)
            continue

        d = find_product_details(m['sku'])

        product_aliases = set()
        if not line.startswith('#'):
            product_aliases = set(find_aliases.search(line)['aliases'].split(','))
        product_aliases.add(d['ean'])

        aliases = ','.join(sorted(product_aliases))
        units = int(m["units"])
        price = d['price']

        # Apply a 30% margin and divide by the number of units per sold packaging.
        unit_price = price * our_margin / units
        # Round up to 5ct.
        unit_price = (unit_price * 20).quantize(Decimal('1'), rounding=ROUND_UP) / 20

        lines_out.append(f'{aliases}\t{unit_price:.2f}\t{d["name"]}  # {m["sku"]} {units}x')

    return '\n'.join(lines_out)
