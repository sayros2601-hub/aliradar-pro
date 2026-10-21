"""The only production update path: recover, validate, audit, rates, build, verify."""
import argparse
from contextlib import contextmanager
from pathlib import Path
import os
from dealvault_core import DATA_DIR, read_json, write_json, validate_catalog, utc_now
from daily_rotator import recover_transaction, rotate_deals
from link_health_guard import audit_catalog
from update_exchange_rates import update_rates
from build_modern_hub import build_site


@contextmanager
def pipeline_lock():
    # OS advisory locks are released automatically even if the process crashes.
    DATA_DIR.mkdir(exist_ok=True)
    path=DATA_DIR/'.pipeline.lock'
    stream=open(path,'a+b')
    stream.seek(0); stream.write(b'0'); stream.flush(); stream.seek(0)
    locked=False
    try:
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        locked=True
        yield
    finally:
        if locked:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
            else:
                fcntl.flock(stream.fileno(),fcntl.LOCK_UN)
        stream.close()


def run(offline=False,rotate=0):
    if offline and rotate:
        raise ValueError('Offline mode cannot run rotation: its destination checks require network access')
    with pipeline_lock():
        recover_transaction()
        db=read_json(DATA_DIR/'products.json')
        validate_catalog(db)
        from published_routes import save_routes
        # Record the old catalog before rotation so existing inbound URLs survive.
        save_routes(db['products'])
        from product_selection import write_selection_report
        write_selection_report()
        if rotate:
            rotate_deals(rotate)
            db=read_json(DATA_DIR/'products.json')
        if not offline:
            audit_catalog(db['products'])
            update_rates()
        output=build_site(db=db)
        save_routes(db['products'])
        from build_bulk_social_csvs import generate_csvs
        generate_csvs(db)
        from build_operator_tools import build_operator_tools
        build_operator_tools()
        from business_health import build_report
        build_report()
        print('[Pipeline] Complete. No social messages were sent.')
        return output


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offline',action='store_true')
    parser.add_argument('--rotate',type=int,default=0)
    args=parser.parse_args()
    run(args.offline,args.rotate)
