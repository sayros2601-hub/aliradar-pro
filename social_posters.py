"""Explicit, opt-in posting for the owner's channels; preview by default."""
import argparse
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dealvault_core import DATA_DIR, DOMAIN, read_json, write_json, utc_now
from marketing_content import social_text
from site_content import COPY


def format_telegram_caption(product,lang='ru',domain=DOMAIN):
    return social_text(product,lang,'telegram',domain),{'inline_keyboard':[[{'text':COPY[lang]['shop'],'url':product['affiliate_url']}]]}


def format_vk_post(product,domain=DOMAIN):
    return social_text(product,'ru','vk',domain),product['affiliate_url']


def request_json(url,payload):
    request=urllib.request.Request(url,data=urllib.parse.urlencode(payload).encode(),headers={'User-Agent':'DealVault/2026.10'})
    for attempt in range(2):
        try:
            with urllib.request.urlopen(request,timeout=20) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            # Retry only a definitive rate-limit refusal. Ambiguous timeouts are not retried.
            if error.code == 429 and attempt == 0:
                try: delay=int(json.load(error).get('parameters',{}).get('retry_after',5))
                except (ValueError,KeyError): delay=5
                if not 0 < delay <= 60: raise RuntimeError('Rate limited; retry later') from None
                time.sleep(delay); continue
            raise RuntimeError(f'Publishing refused with HTTP {error.code}') from None
        except (OSError,ValueError):
            raise RuntimeError('Publishing result uncertain; inspect the channel before retrying') from None


def send_telegram_deal(bot_token,chat_id,caption,reply_markup,image_path=None,simulate=False):
    if simulate:
        print(caption); return True
    result=request_json(f'https://api.telegram.org/bot{bot_token}/sendMessage',{'chat_id':chat_id,'text':caption,'reply_markup':json.dumps(reply_markup),'disable_web_page_preview':'false'})
    return result.get('ok') is True


def send_vk_wall_post(token,owner_id,message,attachments=None,simulate=False):
    if simulate:
        print(message); return True
    result=request_json('https://api.vk.com/method/wall.post',{'access_token':token,'owner_id':owner_id,'message':message,'from_group':1,'v':'5.199'})
    return 'response' in result


def main(platform):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--send',action='store_true',help='Actually send to the explicitly selected owner channel')
    parser.add_argument('--simulate',action='store_true',help='Preview; overrides --send')
    parser.add_argument('--token',default=os.getenv('TELEGRAM_BOT_TOKEN' if platform=='telegram' else 'VK_ACCESS_TOKEN'))
    parser.add_argument('--channel','--chat_id',dest='channel')
    parser.add_argument('--owner_id')
    parser.add_argument('--lang',choices=['en','ru','he','es'],default='ru')
    parser.add_argument('--count',type=int,default=3)
    parser.add_argument('--delay',type=float,default=3)
    parser.add_argument('--repeat',action='store_true',help='Allow re-posting a previously acknowledged product')
    args=parser.parse_args()
    if not 1 <= args.count <= 35:parser.error('--count must be between 1 and 35')
    preview=not args.send or args.simulate
    target=args.channel if platform=='telegram' else args.owner_id
    if not preview and (not args.token or not target):parser.error('Live posting needs a token and an explicit channel/owner_id')
    db=read_json(DATA_DIR/'products.json')
    ledger_path=DATA_DIR/'social_post_log.json'
    ledger=read_json(ledger_path,[])
    sent={entry['key'] for entry in ledger}
    for product in db['products'][:args.count]:
        key=hashlib.sha256(f'{platform}|{target}|{args.lang}|{product["id"]}'.encode()).hexdigest()
        if not preview and key in sent and not args.repeat:
            print('[Skip] Already acknowledged:',product['slug']); continue
        if platform=='telegram':
            caption,buttons=format_telegram_caption(product,args.lang)
            ok=send_telegram_deal(args.token,target,caption,buttons,simulate=preview)
        else:
            text,_=format_vk_post(product)
            ok=send_vk_wall_post(args.token,target,text,simulate=preview)
        if not ok:raise RuntimeError('Publisher did not acknowledge the post; stopped')
        if not preview:
            ledger.append({'key':key,'product_id':product['id'],'platform':platform,'sent_at':utc_now()})
            write_json(ledger_path,ledger[-10000:])
            sent.add(key)
            time.sleep(max(3,args.delay))
    print('[Preview only]' if preview else '[Publishing complete]')
