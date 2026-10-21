"""Export local, unscheduled social drafts. No claims of universal importer compatibility."""
import csv
from dealvault_core import BASE_DIR, DATA_DIR, DOMAIN, LANGUAGES, read_json, page_path
from marketing_content import social_text


def generate_csvs(db=None):
    db=db or read_json(DATA_DIR/'products.json')
    out=BASE_DIR/'broadcasts'/'current'
    out.mkdir(parents=True,exist_ok=True)
    for lang in LANGUAGES:
        with (out/f'dealvault_{lang}.csv').open('w',encoding='utf-8-sig',newline='') as stream:
            writer=csv.writer(stream)
            writer.writerow(['Text','Link','ImageURL','Language'])
            for p in db['products']:
                text=social_text(p,lang)
                # Guard against spreadsheet formula injection in external importers.
                if text.lstrip().startswith(('=','+','-','@')): text="'"+text
                writer.writerow([text,f'{DOMAIN}/{page_path(lang,p["slug"])}',f'{DOMAIN}/{p["image"]}',lang])
    print(f'[Social] {len(db["products"])} drafts × 4 languages exported locally. Nothing scheduled or sent.')


if __name__ == '__main__':
    generate_csvs()
