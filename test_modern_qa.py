"""Compatibility launcher for the headless browser QA with actual assertions."""
import runpy
import sys
from pathlib import Path

if __name__ == '__main__':
    root=Path(__file__).resolve().parent
    sys.argv=[str(root/'tests/browser_qa.py'),'--output',str(root/'.qa')]
    runpy.run_path(str(root/'tests/browser_qa.py'),run_name='__main__')
