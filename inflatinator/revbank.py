from decimal import Decimal, ROUND_UP
import logging
import re
import scrapers

profit_margin = Decimal('1.3')


class AutoUpdate:
    _meta_re = re.compile(r'#\s*(?P<vendor>ah):(?P<sku>\S+)\s+(?P<units>\d+)x$')

    def __init__(self, vendor, sku, units):
        self.vendor = vendor
        self.sku = sku
        self.units = units

    def __str__(self):
        return f'{self.vendor}:{self.sku} {self.units}x'

    @staticmethod
    def from_product_line(line):
        m = AutoUpdate._meta_re.search(line)
        if not m:
            raise Exception('no auto update directive found')
        return AutoUpdate(m['vendor'], m['sku'], int(m['units']))

assert AutoUpdate.from_product_line('# ah:wi162664 8x')
assert AutoUpdate.from_product_line('8711327538481,liuk 0.80  Ola Liuk  # ah:wi162664 8x')


def find_product_details(auto_update):
    if auto_update.vendor == 'ah':
        return scrapers.ah_get_by_sku(auto_update.sku, auto_update.units)
    raise Exception(f'unknown vendor: {auto_update.vendor}')


def update_product_pricings(src):
    find_aliases = re.compile(r'^(?P<aliases>\S+)')

    lines = src.split('\n')
    lines_out = []

    for line in lines:
        try:
            auto_update = AutoUpdate.from_product_line(line)
            logging.debug('Found updatable product: %s', auto_update)
        except Exception as err:
            lines_out.append(line)
            continue

        try:
            prod_info = find_product_details(auto_update)
        except Exception as err:
            logging.error('could not update %s %s: %s', auto_update, err)
            lines_out.append(line)
            continue

        product_aliases = set()
        if not line.startswith('#'):
            product_aliases = set(find_aliases.search(line)['aliases'].split(','))
        product_aliases.add(prod_info.ean)

        aliases = ','.join(sorted(product_aliases))

        # Apply profit margin and divide by the number of units per sold packaging.
        unit_price = prod_info.price * profit_margin / prod_info.units
        # Round up to 5ct.
        unit_price = (unit_price * 20).quantize(Decimal('1'), rounding=ROUND_UP) / 20

        fmt_price = f'{unit_price:.2f}'
        lines_out.append(f'{aliases:<15} {fmt_price:<6} {prod_info.name:<32} # {auto_update}')

        logging.debug(f'Found "{prod_info.name}", buy €{prod_info.price/prod_info.units:.2f}, sell €{fmt_price}')

    return '\n'.join(lines_out)
