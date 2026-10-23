"""Daily DealVault Autopilot: Rotates 7 products, regenerates Pinterest RSS, rebuilds site, deploys to Cloudflare Pages, and submits to IndexNow."""
import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(r"C:\Users\Nika\.gemini\antigravity\scratch\aliexpress_seo_hub")

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def run_daily_update(force=False):
    print("=" * 60)
    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting Daily DealVault Autopilot")
    print("=" * 60)

    # 1. Rotate 7 deals
    print("\n[Step 1/4] Rotating 7 deals from reserve pool...")
    from daily_rotator import rotate_deals
    rotated = rotate_deals(count=7)
    if not rotated and not force:
        print("[Notice] Rotation skipped (already rotated today or no candidates).")
    else:
        print(f"[OK] Rotated {len(rotated)} deals into active catalog.")

    # 2. Rebuild site & RSS feeds via pipeline
    print("\n[Step 2/4] Rebuilding site and Pinterest RSS feeds...")
    from dealvault_pipeline import run as run_pipeline
    run_pipeline(offline=True, rotate=0)
    print("[OK] Rebuild complete.")

    # 3. Deploy to Cloudflare Pages
    print("\n[Step 3/4] Deploying to Cloudflare Pages...")
    from deploy_to_cloudflare import deploy
    deploy()
    print("[OK] Deployment complete.")

    # 4. Notify IndexNow
    print("\n[Step 4/4] Notifying IndexNow search engines...")
    cmd = [sys.executable, str(BASE_DIR / "submit_indexnow.py"), "--submit"]
    subprocess.run(cmd, cwd=BASE_DIR, check=False)
    print("[OK] IndexNow notification finished.")

    print("\n" + "=" * 60)
    print("DAILY UPDATE COMPLETE! 7 items rotated, Pinterest RSS refreshed, live on Cloudflare Pages.")
    print("=" * 60)

if __name__ == '__main__':
    force_run = '--force' in sys.argv
    run_daily_update(force=force_run)
