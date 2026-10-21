"""Compatibility with the old launcher. No fabricated products or freshness timestamps."""
import argparse
from dealvault_pipeline import run


def run_autopilot_cycle():
    return {'ok':True,'output':str(run(rotate=7))}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--once',action='store_true',help='One verified update cycle')
    parser.parse_args()
    run_autopilot_cycle()
