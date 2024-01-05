import revbank
import sys


def main(product_file):
    with open(product_file, 'r') as fd:
        src = fd.read()

    new_src = revbank.update_product_pricings(src)

    with open(product_file, 'w') as fd:
        fd.write(new_src)


if __name__ == '__main__':
    main(sys.argv[1])
