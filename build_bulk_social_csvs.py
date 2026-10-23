"""Export local, unscheduled social drafts. No claims of universal importer compatibility."""
import csv
import sys
from dealvault_core import BASE_DIR, DATA_DIR, DOMAIN, LANGUAGES, read_json, page_path, public_path
from marketing_content import social_text

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


def generate_csvs(db=None):
    db=db or read_json(DATA_DIR/'products.json')
    out=BASE_DIR/'broadcasts'/'current'
    out.mkdir(parents=True,exist_ok=True)
    editorial=read_json(DATA_DIR/'editorial.json',{'products':{}})['products']
    for lang in LANGUAGES:
        with (out/f'dealvault_{lang}.csv').open('w',encoding='utf-8-sig',newline='') as stream:
            writer=csv.writer(stream)
            writer.writerow(['Text','Link','ImageURL','Language'])
            for p in db['products']:
                text=social_text(p,lang,editorial_map=editorial)
                # Guard against spreadsheet formula injection in external importers.
                if text.lstrip().startswith(('=','+','-','@')): text="'"+text
                writer.writerow([text,f'{DOMAIN}{public_path(page_path(lang,p["slug"]))}',f'{DOMAIN}/{p["image"]}',lang])
    print(f'[Social] {len(db["products"])} drafts x 4 languages exported locally. Nothing scheduled or sent.')


if __name__ == '__main__':
    generate_csvs()
