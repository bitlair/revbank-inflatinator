from decimal import Decimal, ROUND_UP
import logging
import re
import scrapers

profit_margin = Decimal('1.3')


class AutoUpdate:
    _ah_meta_re = re.compile(r'#\s*ah:(?P<sku>\S+)\s+(?P<units>\d+)x$')
    _sligro_meta_re = re.compile(r'^(?P<gtin13>\d{13})[^#]+#\s*sligro$')

    def __init__(self, vendor, sku, units):
        self.vendor = vendor
        self.sku = sku
        self.units = units

    def __str__(self):
        if self.vendor == 'sligro':
            return f'{self.vendor}'
        if self.units:
            return f'{self.vendor}:{self.sku} {self.units}x'
        return f'{self.vendor}:{self.sku}'

    @staticmethod
    def from_product_line(line):
        ah = AutoUpdate._ah_meta_re.search(line)
        if ah:
            return AutoUpdate('ah', ah['sku'], int(ah['units']))

        sligro = AutoUpdate._sligro_meta_re.search(line)
        if sligro:
            return AutoUpdate('sligro', sligro['gtin13'], None)

        raise Exception('no auto update directive found')

assert AutoUpdate.from_product_line('# ah:wi162664 8x')
assert AutoUpdate.from_product_line('8711327538481,liuk 0.80  Ola Liuk  # ah:wi162664 8x')
assert AutoUpdate.from_product_line('5000112659184 # sligro')
assert AutoUpdate.from_product_line('5000112659184 1.00  Cola Zero  # sligro')
assert AutoUpdate.from_product_line('5000112659184,colazero 1.00  Cola Zero  # sligro')


def find_product_details(auto_update):
    if auto_update.vendor == 'ah':
        return scrapers.ah_get_by_sku(auto_update.sku, auto_update.units)
    if auto_update.vendor == 'sligro':
        return scrapers.sligro_get_by_gtin(auto_update.sku)
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
            logging.error('could not update %s: %s', auto_update, err)
            lines_out.append(line)
            continue

        product_aliases = set()
        if not line.startswith('#'):
            human_aliases = set(find_aliases.search(line)['aliases'].split(','))
            human_aliases -= set([prod_info.gtin])
            human_aliases -= set(prod_info.aliases)
            human_aliases = sorted(human_aliases)
        scannables = ','.join([prod_info.gtin, *prod_info.aliases, *human_aliases])

        # Apply profit margin and divide by the number of units per sold packaging.
        unit_price = prod_info.price * profit_margin / prod_info.units
        # Round up to 5ct.
        unit_price = (unit_price * 20).quantize(Decimal('1'), rounding=ROUND_UP) / 20

        fmt_price = f'{unit_price:.2f}'
        lines_out.append(f'{scannables:<30} {fmt_price:<6} {prod_info.name:<60} # {auto_update}')

        logging.debug(f'Found "{prod_info.name}", buy €{prod_info.price/prod_info.units:.2f}, sell €{fmt_price}')

    return '\n'.join(lines_out)
