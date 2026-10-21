"""Compatibility API for trusted local callers; the old unauthenticated admin is retired."""
from dealvault_core import BASE_DIR, DATA_DIR, read_json, write_json, validate_catalog
from build_modern_hub import build_site


def load_db():
    return read_json(DATA_DIR/'products.json')


def save_db(db):
    validate_catalog(db)
    write_json(DATA_DIR/'products.json',db)


def build_all():
    return build_site()


if __name__ == '__main__':
    build_all()
