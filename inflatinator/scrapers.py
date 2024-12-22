from decimal import Decimal
from functools import reduce
from pyquery import PyQuery as pq
import json
import re
import os
import requests
import subprocess
import logging


vat = Decimal('1.09')


class Product:
    def __init__(self, *, name, price, gtin, units, aliases=[]):
        self.name = name
        self.price = price
        self.gtin = gtin
        self.units = units
        self.aliases = aliases

    def __str__(self):
        return self.name


def links_get(url):
    compl = subprocess.run(['links', '-source', url], capture_output=True)
    return compl.stdout


def ah_get_by_sku(ah_sku, units):
    assert re.match(r'^wi\d+$', ah_sku)

    html_src = links_get(f'https://www.ah.nl/producten/product/{ah_sku}')
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
        gtin=schema['gtin13'],
        units=units,
    )


_sess = requests.Session()

def sligro_client():
    global _sess

    if _sess.cookies:
        return _sess

    username = os.getenv('SLIGRO_USERNAME')
    password = os.getenv('SLIGRO_PASSWORD')
    if not username:
        raise Exception('missing SLIGRO_USERNAME')
    if not password:
        raise Exception('missing SLIGRO_PASSWORD')

    resp = _sess.post('https://www.sligro.nl/api/user/sligro-nl/nl/login',
                      json={'username': username, 'password': password, 'rememberMe': False})
    resp.raise_for_status()
    logging.info('Sligro login ok!')

    return _sess


def sligro_get_by_gtin(gtin13):
    assert re.match(r'^\d{13}$', gtin13)
    gtin14 = f'{gtin13:0>14}'

    # The search feature of the website returns results in JSON and handles GTIN formats. Neat!
    # However, it can be a bit picky about leading zeros, so we try to query with GTIN14 as that is
    # what works in the most cases. Sometimes GTIN13 is still required though
    for gtin_whatever in [gtin14, gtin13]:
        response = requests.get(f'https://www.sligro.nl/api/product-overview/sligro-nl/nl/query/3?term={gtin_whatever}')
        response.raise_for_status()
        body = response.json()
        if 'products' in body:
            break
    else:
        raise Exception(f'sligro: {gtin13} not found')

    product = body['products'][0]
    sku = product["code"]

    # Query the product page itself, there is more info that we need on there. The 'url' field in
    # the product object gives a 404, but the actual product page URL can be created from the search
    # results.
    url_slug = '-'.join([product['brandName'], product['name'], product['contentDescription']])\
        .replace(' ', '-')\
        .replace('\'', '-')\
        .replace('&', '-')\
        .replace(',', '')\
        .replace('%', '')\
        .lower()
    prod_resp = requests.get(f'https://www.sligro.nl/p.{sku}.html/{url_slug}.html')
    prod_resp.raise_for_status()

    product_page = pq(prod_resp.text)
    prod_ext_data_script = product_page('script[data-hypernova-key="ProductDetail"]')
    prod_ext_data = json.loads(prod_ext_data_script[0].text.replace('<!--', '').replace('-->', ''))

    # Most products contain products which have distinct barcodes.
    sub_gtin = prod_ext_data['propsData']['data'].get('gtinUnderlyingUnit', None)
    if sub_gtin:
        sub_gtin = sub_gtin.lstrip('0')

    # The contentDescription field holds the number of individual packages per box sold.
    units, volume = parse_content_description(product['contentDescription'])

    # Pricing requires logging in and is on a separate endpoint...
    pricing_resp = sligro_client().get(f'https://www.sligro.nl/api/cart/sligro-nl/customerorganizationdatas?productCodes={sku}')
    pricing = pricing_resp.json()['data']['products'][0]

    # If fromPrice is present, this product has a temporary discount. We prefer the regular price as
    # we do not want to make a loss on stock that was purchased earlier.
    if (from_price := pricing.get('fromPrice')):
        price_obj = from_price
    else:
        price_obj = pricing['price']

    return Product(
        name=f'{product["brandName"]} {product["name"]} ({volume})',
        price=Decimal(price_obj['value']) * vat,
        gtin=gtin13,
        units=units,
        aliases=[sub_gtin] if sub_gtin else [],
    )


# The contentDescription seems to have a formatting consistent enough for regex matching. Some
# products have multiple levels of packaging, but the last or only component is always the
# volume or weight.
def parse_content_description(cd):
    # These ones are weird.
    if cd.endswith(' rollen'):
        return int(cd.split(' ')[0]), 'rol'
    if (m := re.search(r'^Pak (\d+) stuks$', cd)):
        return int(m[1]), ''
    if (m := re.search(r'^(\d+) Flessen (\d+ CL)$', cd)):
        return int(m[1]), m[2]

    groups = re.split(r'\s+x\s+', cd)
    volume = groups[-1]
    unit_groups = groups[:-1]

    sub_units = (int(re.search(r'(\d+)', g)[0]) for g in unit_groups)
    units = reduce(lambda a, b: a * b, sub_units, 1)

    return units, volume
