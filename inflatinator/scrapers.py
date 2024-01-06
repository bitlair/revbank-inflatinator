from decimal import Decimal
from pyquery import PyQuery as pq
import json
import re
import subprocess


class Product:
    def __init__(self, name, price, ean, units):
        self.name = name
        self.price = price
        self.ean = ean
        self.units = units

    def __str__(self):
        return self.name


def get(url):
    compl = subprocess.run(['links', '-source', url], capture_output=True)
    return compl.stdout


def ah_get_by_sku(ah_sku, units):
    assert re.match('^wi\d+$', ah_sku)

    html_src = get(f'https://www.ah.nl/producten/product/{ah_sku}')
    doc = pq(html_src)

    ld_jsons = doc('script[type="application/ld+json"]')
    for j in ld_jsons:
        schema = json.loads(j.text)
        if schema['@type'] == 'Product' and schema['sku'] == ah_sku:
            break
    else:
        raise Exception(f'ah.nl returned no JSON metadata for SKU {ah_sku}')

    return Product(
        name=schema['name'],
        price=Decimal(schema['offers']['price']),
        ean=schema['gtin13'],
        units=units,
    )
