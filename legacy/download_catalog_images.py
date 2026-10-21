import os
import json
import time
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "products.json")
IMG_DIR = os.path.join(BASE_DIR, "assets", "img")
os.makedirs(IMG_DIR, exist_ok=True)

with open(DATA_FILE, "r", encoding="utf-8") as f:
    db = json.load(f)

products = db.get("products", [])
print(f"Total products to process: {len(products)}")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
}

def download_file(url, target_path):
    if os.path.exists(target_path) and os.path.getsize(target_path) > 1000:
        return True
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = resp.read()
            if len(data) > 500:
                with open(target_path, "wb") as out:
                    out.write(data)
                return True
    except Exception as e:
        print(f"  Error downloading {url}: {e}")
    return False

for p in products:
    slug = p.get("slug", p["id"])
    gallery = p.get("gallery", [])
    if not gallery and p.get("image"):
        gallery = [p["image"]]
    
    local_gallery = []
    print(f"Processing {p['id']} ({slug})...")
    
    for idx, remote_url in enumerate(gallery):
        ext = ".png" if ".png" in remote_url else ".jpg"
        filename = f"{slug}-{idx+1}{ext}"
        local_path = os.path.join(IMG_DIR, filename)
        web_path = f"assets/img/{filename}"
        
        ok = download_file(remote_url, local_path)
        if ok:
            local_gallery.append(web_path)
            print(f"  [OK] Saved {filename} ({os.path.getsize(local_path)} bytes)")
        else:
            # Fallback to remote if failed
            local_gallery.append(remote_url)
            print(f"  [WARN] Fallback remote for {filename}")
        
        # gentle delay to avoid CDN rate limiting
        time.sleep(0.35)

    if local_gallery:
        p["image"] = local_gallery[0]
        p["gallery"] = local_gallery

with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(db, f, ensure_ascii=False, indent=2)

print("\nSuccessfully updated products.json with local cached images!")
