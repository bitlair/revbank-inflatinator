import revbank
import sys
import logging


def main(product_file):
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    with open(product_file, 'r') as fd:
        src = fd.read()

    new_src = revbank.update_product_pricings(src)

    with open(product_file, 'w') as fd:
        fd.write(new_src)


if __name__ == '__main__':
    main(sys.argv[1])
