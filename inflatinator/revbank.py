from dataclasses import dataclass
from decimal import Decimal, ROUND_UP
from typing import Dict, Optional, List
import logging
import re
import scrapers
import shlex

profit_margin = Decimal('1.3')


@dataclass
class Product:
    aliases: List[str]
    price: Decimal
    description: str
    metadata: Dict[str, Optional[str]]

    @staticmethod
    def from_line(line: str) -> "Product":
        if not line.strip():
            raise Exception('line is empty')
        if line.startswith('#'):
            raise Exception('line is a comment')

        fields = shlex.split(line)
        aliases = fields[0].split(',')
        price = Decimal(fields[1])
        description = fields[2]
        # TODO: support addons

        metadata = {}
        for f in fields:
            if f.startswith('#'):
                s = f.lstrip('#').split('=')
                (k, v) = (s[0], None) if len(s) == 1 else s
                metadata[k] = v

        return Product(
            aliases=aliases,
            price=price,
            description=description,
            metadata=metadata,
        )

    def format_line(self):
        aliases = ','.join(self.aliases)
        price = f'{self.price:.2f}'
        description = f'"{self.description}"'
        metadata = ' '.join(sorted(f'#{k}' if v is None else f'#{k}={v}' for (k, v) in self.metadata.items()))
        return f'{aliases:<30} {price:<6} {description:<60} {metadata}'


assert Product.from_line('8711327538481,liuk 0.80 "Ola Liuk" #ah=wi162664 #qty=8') == \
    Product(['8711327538481','liuk'], Decimal('0.8'), 'Ola Liuk', {'ah': 'wi162664', 'qty': '8'})
assert Product.from_line('5000112659184,colazero 1.00 "Cola Zero" #sligro') == \
    Product(['5000112659184','colazero'], Decimal(1), 'Cola Zero', {'sligro': None})
assert Product.from_line('8711327538481,liuk 0.80 "Ola Liuk" #ah=wi162664 #qty=8').format_line() == \
    '8711327538481,liuk             0.80   "Ola Liuk"                                                   #ah=wi162664 #qty=8'
assert Product(['5000112659184','colazero'], Decimal(1), 'Cola Zero', {'sligro': None}).format_line() == \
    '5000112659184,colazero         1.00   "Cola Zero"                                                  #sligro'


class NoAutoUpdate(Exception):
    def __init__(self):
        super().__init__('no auto update directive')


def find_product_details(product: Product):
    if 'ah' in product.metadata:
        return scrapers.ah_get_by_gtin(product.aliases[0])
    if 'sligro' in product.metadata:
        return scrapers.sligro_get_by_gtin(product.aliases[0])
    raise NoAutoUpdate()


def update_product_pricings(src):
    lines_out = []
    for line in src.split('\n'):
        try:
            product = Product.from_line(line)
        except Exception as err:
            lines_out.append(line)
            continue

        try:
            prod_info = find_product_details(product)
        except NoAutoUpdate:
            logging.debug('no auto update: %s', product)
            lines_out.append(line)
            continue
        except Exception as err:
            logging.error('did not update %s: %s', product, err)
            lines_out.append(line)
            continue

        human_aliases = sorted(set(product.aliases) - set([prod_info.gtin]) - set(prod_info.aliases))
        product.aliases = [prod_info.gtin, *prod_info.aliases, *human_aliases]

        # Apply profit margin and divide by the number of units per sold packaging.
        unit_price = prod_info.price * profit_margin / prod_info.units
        # Round up to 5ct.
        previous_price = product.price
        product.price = (unit_price * 20).quantize(Decimal('1'), rounding=ROUND_UP) / 20

        lines_out.append(product.format_line())

        logging.debug(f'Found "{prod_info.name}", buy €{prod_info.price/prod_info.units:.2f}, sell €{product.price:.2f}')
        if product.price != previous_price:
            logging.info(f'Adjusted "{prod_info.name}", €{previous_price:.2f} -> €{product.price:.2f}')

    return '\n'.join(lines_out)
