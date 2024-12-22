from scrapers import *


def test_scrape_ah():
    # Ola Liuk
    prod = ah_get_by_gtin('8711327538481')
    assert type(prod) is Product
    assert prod.name == 'Ola Liuk'
    assert prod.gtin == '8711327538481'
    assert prod.units == 8
    assert prod.aliases == []


def test_scrape_sligro():
    # Cola zero sugar
    prod = sligro_get_by_gtin('5000112659184')
    assert type(prod) is Product
    assert prod.name == 'Coca-Cola Cola zero sugar (33 cl)'
    assert prod.gtin == '5000112659184'
    assert prod.units == 24
    assert prod.aliases == ['5000112658873']


def test_parse_content_description():
    assert parse_content_description('40 stuks x 22,5 gram') == (40, '22,5 gram')
    assert parse_content_description('4 multipacks x 6 blikjes x 33 cl') == (24, '33 cl')
    assert parse_content_description('24  2-packs x 70 gram') == (24, '70 gram')
    assert parse_content_description('Tray 12 x 40 gram') == (12, '40 gram')
    assert parse_content_description('36 rollen') == (36, 'rol')
    assert parse_content_description('Pak 10 stuks') == (10, '')
    assert parse_content_description('9 Flessen 50 CL') == (9, '50 CL')
