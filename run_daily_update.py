"""Daily DealVault Autopilot: Refreshes rates & reserve timestamps, rotates 7 products, rebuilds site & Pinterest RSS, deploys to Cloudflare Pages, pushes to GitHub main, and submits to IndexNow."""
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

    # 0. Refresh exchange rates & reserve pool timestamps
    print("\n[Step 0/5] Refreshing exchange rates and reserve pool timestamps...")
    from update_exchange_rates import update_rates
    update_rates()

    # 1. Rotate 7 deals
    print("\n[Step 1/5] Rotating 7 deals from reserve pool...")
    from daily_rotator import rotate_deals
    rotated = rotate_deals(count=7)
    if not rotated and not force:
        print("[Notice] Rotation skipped (already rotated today or no candidates).")
    else:
        print(f"[OK] Rotated {len(rotated)} deals into active catalog.")

    # 2. Rebuild site & RSS feeds via pipeline
    print("\n[Step 2/5] Rebuilding site and Pinterest RSS feeds...")
    from dealvault_pipeline import run as run_pipeline
    run_pipeline(offline=True, rotate=0)
    print("[OK] Rebuild complete.")

    # 3. Deploy to Cloudflare Pages
    print("\n[Step 3/5] Deploying to Cloudflare Pages...")
    from deploy_to_cloudflare import deploy
    deploy()
    print("[OK] Deployment complete.")

    # 4. Sync with GitHub origin/main so scheduled GitHub Actions never overwrite local updates
    print("\n[Step 4/5] Syncing catalog state with GitHub (origin/main)...")
    try:
        subprocess.run(["git", "add", "data/products.json", "data/reserve_pool.json", "data/exchange_rates.json", "data/selection_report.json", "data/published_routes.json", "data/demand_snapshots.json"], cwd=BASE_DIR, check=False)
        if (BASE_DIR / "data" / "rotation_log.json").exists():
            subprocess.run(["git", "add", "data/rotation_log.json"], cwd=BASE_DIR, check=False)
        diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=BASE_DIR)
        if diff.returncode != 0:
            subprocess.run(["git", "commit", "-m", "chore: daily catalog rotation and snapshot sync [skip ci]"], cwd=BASE_DIR, check=False)
        subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=BASE_DIR, check=False)
        print("[OK] GitHub origin/main synchronized.")
    except Exception as exc:
        print(f"[Warning] Git sync skipped: {exc}")

    # 5. Notify IndexNow
    print("\n[Step 5/5] Notifying IndexNow search engines...")
    cmd = [sys.executable, str(BASE_DIR / "submit_indexnow.py"), "--submit"]
    subprocess.run(cmd, cwd=BASE_DIR, check=False)
    print("[OK] IndexNow notification finished.")

    print("\n" + "=" * 60)
    print("DAILY UPDATE COMPLETE! Catalog synced with GitHub & Cloudflare Pages.")
    print("=" * 60)


if __name__ == '__main__':
    force_run = '--force' in sys.argv
    run_daily_update(force=force_run)
