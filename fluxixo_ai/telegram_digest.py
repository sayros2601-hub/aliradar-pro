"""Automated Telegram product digest & ops alert utility for FLUXIXO."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from html import escape as e
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request

REPO_ROOT = Path(__file__).resolve().parents[1]
SITE_ORIGIN = 'https://www.fluxixo.shop'
MEDIA_ORIGIN = 'https://media.fluxixo.shop'
DEFAULT_AUTOPILOT_URL = 'https://fluxixo-autopilot.sayros2601.workers.dev'
DEFAULT_STATE_PATH = REPO_ROOT / 'data' / 'telegram_digest_state.json'
DEFAULT_PUBLISH_STATE = REPO_ROOT / 'data' / 'fluxixo_publish_state.json'
DEFAULT_LINK_REPORT = REPO_ROOT / 'data' / 'link_health_report.json'
DEFAULT_CATALOG_JS = REPO_ROOT / 'fluxixo_site' / 'dist' / 'js' / 'catalog.js'
DEFAULT_I18N = REPO_ROOT / 'fluxixo_site' / 'tools' / 'i18n_data.json'


def load_catalog_products(catalog_path: Path = DEFAULT_CATALOG_JS) -> list[dict]:
    if not catalog_path.is_file():
        return []
    raw = catalog_path.read_text(encoding='utf-8').strip()
    if '=' in raw:
        raw = raw.split('=', 1)[1].strip().rstrip(';')
    data = json.loads(raw)
    items = data.get('products', []) if isinstance(data, dict) else data
    return [p for p in items if isinstance(p, dict) and not p.get('demo')]


def fetch_clicks_summary(days: int = 7) -> dict | None:
    base_url = (os.environ.get('CLOUDFLARE_AUTOPILOT_URL') or DEFAULT_AUTOPILOT_URL).strip().rstrip('/')
    sync_token = (os.environ.get('AUTOPILOT_SYNC_TOKEN') or '').strip()
    if not base_url or not sync_token:
        return None
    req = urllib.request.Request(
        f'{base_url}/api/clicks-summary?days={int(days)}',
        headers={'Authorization': f'Bearer {sync_token}', 'User-Agent': 'FLUXIXO-Digest/1.0'},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read(1_000_000).decode('utf-8'))
        return data if data.get('ok') else None
    except Exception:
        return None


def build_digest_payload(
    products: list[dict],
    i18n: dict | None = None,
    *,
    clicks_summary: dict | None = None,
    limit: int = 5,
    weekly: bool = False,
) -> dict:
    """Build structured JSON digest and ready-to-send HTML text for Telegram."""
    i18n_prods = (i18n or {}).get('products', {})
    recent = []
    for p in products[:max(1, limit)]:
        pid = str(p.get('id', ''))
        en_tr = i18n_prods.get(pid, {}).get('en') or {}
        img_rel = str(p.get('image') or '').lstrip('/')
        recent.append({
            'id': pid,
            'name_ru': str(p.get('name') or ''),
            'name_en': str(en_tr.get('name') or p.get('name') or ''),
            'category': str(p.get('category') or ''),
            'description_ru': str(p.get('description') or ''),
            'url_ru': f'{SITE_ORIGIN}/products/{pid}/',
            'url_en': f'{SITE_ORIGIN}/en/products/{pid}/',
            'image_url': f'{MEDIA_ORIGIN}/{img_rel}' if img_rel else '',
        })

    heading = 'Еженедельный дайджест FLUXIXO' if weekly else 'Новые находки на FLUXIXO'
    lines = [f'<b>{e(heading)}</b>', '']
    for item in recent:
        lines.append(
            f'• <a href="{e(item["url_ru"])}">{e(item["name_ru"])}</a> '
            f'<i>({e(item["category"])})</i> — {e(item["description_ru"][:120])}'
        )
    if clicks_summary and int(clicks_summary.get('total_clicks') or 0) > 0:
        lines.append('')
        lines.append(f'<b>Клики за {int(clicks_summary.get("days", 7))} дн.:</b> {int(clicks_summary["total_clicks"])}')
        for top in (clicks_summary.get('top_products') or [])[:3]:
            lines.append(f'  — <code>{e(str(top.get("product_id")))}</code>: {int(top.get("clicks", 0))}')
    lines.append('')
    lines.append(f'<a href="{SITE_ORIGIN}/catalog/">Открыть каталог FLUXIXO</a>')
    text = '\n'.join(lines)[:3800]

    return {
        'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'weekly': bool(weekly),
        'total_catalog': len(products),
        'items': recent,
        'clicks_summary': clicks_summary,
        'message_html': text,
    }


def collect_ops_alerts(
    publish_state_path: Path = DEFAULT_PUBLISH_STATE,
    link_report_path: Path = DEFAULT_LINK_REPORT,
    *,
    now: datetime | None = None,
    explicit_reason: str = '',
) -> list[str]:
    """Return human-readable ops alerts when publishing stalls or links fail persistently."""
    alerts: list[str] = []
    current = now or datetime.now(timezone.utc)
    if explicit_reason:
        alerts.append(f'Workflow alert: {explicit_reason}')

    if publish_state_path.is_file():
        try:
            ps = json.loads(publish_state_path.read_text(encoding='utf-8'))
            days = ps.get('days') or {}
            published_days = [
                str(row.get('published_day') or day)
                for day, row in days.items()
                if isinstance(row, dict) and row.get('status') == 'published'
            ]
            if published_days:
                latest_str = max(published_days)
                latest_dt = datetime.fromisoformat(f'{latest_str}T12:00:00+00:00')
                age_hours = (current - latest_dt).total_seconds() / 3600.0
                # Allow 42h window so normal Sunday rest day never triggers a false stall alarm.
                if age_hours > 42.0:
                    alerts.append(f'Catalog publish stall: last published {latest_str} ({age_hours:.1f}h ago)')
        except (OSError, ValueError):
            alerts.append('Publish state file unreadable')

    if link_report_path.is_file():
        try:
            rep = json.loads(link_report_path.read_text(encoding='utf-8'))
            broken = [
                r for r in (rep.get('results') or [])
                if isinstance(r, dict) and r.get('status') != 'RESOLVED' and int(r.get('broken_streak') or 0) >= 3
            ]
            if broken:
                sample = ', '.join(f"{r.get('id')} ({r.get('reason')})" for r in broken[:5])
                alerts.append(f'Persistent broken affiliate links ({len(broken)}): {sample}')
        except (OSError, ValueError):
            pass

    return alerts


def send_telegram_message(text: str, *, chat_id: str | None = None) -> dict:
    """Send Telegram HTML message via direct Bot API or Worker `/api/telegram-digest`."""
    bot_token = (os.environ.get('TELEGRAM_BOT_TOKEN') or '').strip()
    target_chat = (chat_id or os.environ.get('TELEGRAM_CHAT_ID') or '').strip()
    if bot_token and target_chat:
        body = json.dumps({
            'chat_id': target_chat,
            'text': text[:4000],
            'parse_mode': 'HTML',
            'disable_web_page_preview': False,
        }, ensure_ascii=False).encode('utf-8')
        req = urllib.request.Request(
            f'https://api.telegram.org/bot{bot_token}/sendMessage',
            data=body,
            headers={'Content-Type': 'application/json; charset=utf-8'},
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read(200_000).decode('utf-8'))

    autopilot_url = (os.environ.get('CLOUDFLARE_AUTOPILOT_URL') or '').strip().rstrip('/')
    sync_token = (os.environ.get('AUTOPILOT_SYNC_TOKEN') or '').strip()
    if autopilot_url and sync_token:
        body = json.dumps({'text': text[:4000], 'parse_mode': 'HTML', 'chat_id': target_chat}, ensure_ascii=False).encode('utf-8')
        req = urllib.request.Request(
            f'{autopilot_url}/api/telegram-digest',
            data=body,
            headers={'Authorization': f'Bearer {sync_token}', 'Content-Type': 'application/json; charset=utf-8'},
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read(200_000).decode('utf-8'))

    return {'ok': True, 'skipped': 'missing_telegram_secrets'}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('digest', 'alert'), default='digest')
    parser.add_argument('--weekly', action='store_true')
    parser.add_argument('--limit', type=int, default=5)
    parser.add_argument('--write-json', default='')
    parser.add_argument('--state', default=str(DEFAULT_STATE_PATH))
    parser.add_argument('--reason', default='')
    parser.add_argument('--summary', default='')
    args = parser.parse_args()

    if args.mode == 'digest':
        products = load_catalog_products()
        i18n = json.loads(DEFAULT_I18N.read_text(encoding='utf-8')) if DEFAULT_I18N.is_file() else {}
        clicks = fetch_clicks_summary(7)
        payload = build_digest_payload(products, i18n, clicks_summary=clicks, limit=args.limit, weekly=args.weekly)
        if args.write_json:
            out = Path(args.write_json)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
        top_id = payload['items'][0]['id'] if payload['items'] else ''
        state_file = Path(args.state)
        state = json.loads(state_file.read_text(encoding='utf-8')) if state_file.is_file() else {}
        dedup_key = f'weekly:{datetime.now(timezone.utc).strftime("%Y-W%W")}' if args.weekly else f'drop:{top_id}'
        if state.get('last_sent_key') == dedup_key:
            print(f'[telegram_digest] skipped duplicate ({dedup_key})')
            return 0
        try:
            res = send_telegram_message(payload['message_html'])
            print(f'[telegram_digest] send result: {json.dumps(res, ensure_ascii=False)}')
            if res.get('ok') and not res.get('skipped'):
                state['last_sent_key'] = dedup_key
                state['sent_at'] = payload['generated_at']
                state_file.parent.mkdir(parents=True, exist_ok=True)
                state_file.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8', newline='\n')
        except Exception as exc:
            print(f'[telegram_digest] warning (non-blocking): {exc}', file=sys.stderr)
        return 0

    alerts = collect_ops_alerts(explicit_reason=args.reason)
    if args.summary:
        Path(args.summary).parent.mkdir(parents=True, exist_ok=True)
        with Path(args.summary).open('a', encoding='utf-8') as fh:
            if alerts:
                fh.write('### Ops Alerts\n' + '\n'.join(f'- {a}' for a in alerts) + '\n\n')
            else:
                fh.write('### Ops Health\n- All scheduled checks healthy.\n\n')
    if not alerts:
        print('[telegram_digest] ops health OK (no alerts)')
        return 0
    alert_chat = (os.environ.get('TELEGRAM_ALERT_CHAT_ID') or os.environ.get('TELEGRAM_CHAT_ID') or '').strip()
    msg = '<b>FLUXIXO Ops Alert</b>\n' + '\n'.join(f'• {e(a)}' for a in alerts)
    try:
        res = send_telegram_message(msg, chat_id=alert_chat)
        print(f'[telegram_digest] alert result: {json.dumps(res, ensure_ascii=False)}')
    except Exception as exc:
        print(f'[telegram_digest] alert warning (non-blocking): {exc}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
