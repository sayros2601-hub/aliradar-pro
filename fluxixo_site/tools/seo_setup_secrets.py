"""One-time setup, run by the site owner on this PC: puts keys into DPAPI, GitHub Secrets, and Cloudflare Worker.

Keys never pass through chat: this script reads them from .local/*.dpapi (or prompts without echo)
and pipes them via standard input to `gh secret set` and `wrangler secret put` (`fluxixo-autopilot`).

  python fluxixo_site/tools/seo_setup_secrets.py                      Bing + SEO + saved AI/Autopilot keys
  python fluxixo_site/tools/seo_setup_secrets.py --yandex             also asks for a new Yandex token
  python fluxixo_site/tools/seo_setup_secrets.py --google-json FILE   also adds the Google service-account key
  python fluxixo_site/tools/seo_setup_secrets.py --gemini-key         save Google AI Studio key -> GitHub + Worker
  python fluxixo_site/tools/seo_setup_secrets.py --worker-only        sync Worker secrets only via Wrangler
"""
import argparse
import getpass
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dpapi_store import load_credential, save_credential  # noqa: E402

REPO = 'sayros2601-hub/aliradar-pro'
WORKER_NAME = 'fluxixo-autopilot'
HUB_ROOT = Path(__file__).resolve().parents[2]
WORKER_DIR = HUB_ROOT / 'cloudflare_autopilot'
LOG = HUB_ROOT / '.local/seo-setup-log.txt'


def say(text):
    """Print and keep a copy (never a key) so a closed window can still be diagnosed."""
    print(text, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open('a', encoding='utf-8') as stream:
        stream.write(text + '\n')


def gh_ready():
    return subprocess.run(['gh', 'auth', 'status', '--hostname', 'github.com'],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0


def login():
    if gh_ready():
        say('  GitHub: вход уже выполнен.')
        return
    say('  Нужно один раз войти в GitHub:')
    say('   - спросит "Authenticate Git" - нажмите Enter;')
    say('   - появится код (он уже скопирован) - нажмите Enter, откроется браузер;')
    say('   - в браузере: Ctrl+V, Continue, Authorize github, потом вернитесь в это окно.')
    subprocess.run(['gh', 'auth', 'login', '--hostname', 'github.com', '--git-protocol', 'https', '--web'])
    if not gh_ready():
        raise SystemExit('  Вход в GitHub не выполнен. Запустите файл ещё раз.')
    say('  GitHub: вход выполнен.')


def _sanitize_error(text, secret=''):
    msg = (text or '').strip()
    if secret:
        msg = msg.replace(secret, '***')
    return msg


def put(name, value):
    result = subprocess.run(['gh', 'secret', 'set', name, '--repo', REPO], input=value.encode('utf-8'),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        err = _sanitize_error(result.stderr.decode('utf-8', 'replace'), value)
        raise SystemExit(f'gh secret set {name} failed: {err}')
    say(f'  {name}: сохранён в GitHub')


def resolve_wrangler_cmd():
    """Locate Wrangler CLI without leaking or prompting for tokens."""
    suffix = '.cmd' if os.name == 'nt' else ''
    for base in (WORKER_DIR, HUB_ROOT):
        cand = base / 'node_modules' / '.bin' / f'wrangler{suffix}'
        if cand.is_file():
            return [str(cand.resolve())]
    found = shutil.which('wrangler')
    if found:
        return [found]
    npx = shutil.which(f'npx{suffix}')
    if npx:
        return [npx, '--no-install', 'wrangler']
    return None


def wrangler_ready(wrangler_cmd):
    """Return True when Wrangler CLI is runnable and authenticated in WORKER_DIR."""
    if not wrangler_cmd or not WORKER_DIR.is_dir():
        return False
    try:
        res = subprocess.run([*wrangler_cmd, 'whoami'], cwd=str(WORKER_DIR),
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
        return res.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def put_worker_secret(wrangler_cmd, name, value):
    """Upload a single secret via stdin to Cloudflare Worker `fluxixo-autopilot`."""
    res = subprocess.run(
        [*wrangler_cmd, 'secret', 'put', name, '--name', WORKER_NAME],
        cwd=str(WORKER_DIR),
        input=value.encode('utf-8'),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    if res.returncode != 0:
        raw_err = res.stderr.decode('utf-8', 'replace') or res.stdout.decode('utf-8', 'replace')
        raise RuntimeError(_sanitize_error(raw_err, value) or f'exit code {res.returncode}')
    say(f'  {name}: сохранён в Cloudflare Worker ({WORKER_NAME})')


def clean_token(text):
    """Pasting into a terminal can wrap the text in bracketed-paste codes or add spaces; keep only token characters."""
    text = re.sub(r'\x1b\[20[01]~', '', text or '')
    return ''.join(ch for ch in text if ch.isalnum() or ch in '_-.=+/')


def yandex_check(token):
    """None when the token can read fluxixo.shop statistics, else the reason (never the token itself)."""
    if len(token) < 30:
        return f'токен пустой или обрезан ({len(token)} символов)'
    step = 'user'
    try:
        request = urllib.request.Request('https://api.webmaster.yandex.net/v4/user', headers={'Authorization': f'OAuth {token}'})
        with urllib.request.urlopen(request, timeout=20) as response:
            user = json.loads(response.read())['user_id']
        step = 'hosts'
        hosts = urllib.request.Request(f'https://api.webmaster.yandex.net/v4/user/{user}/hosts',
                                       headers={'Authorization': f'OAuth {token}'})
        with urllib.request.urlopen(hosts, timeout=20) as response:
            host = next(h['host_id'] for h in json.loads(response.read())['hosts'] if 'www.fluxixo.shop' in h['host_id'])
        step = 'summary'
        summary = urllib.request.Request(
            f'https://api.webmaster.yandex.net/v4/user/{user}/hosts/{urllib.request.quote(host, safe="")}/summary',
            headers={'Authorization': f'OAuth {token}'})
        with urllib.request.urlopen(summary, timeout=20):
            return None
    except urllib.error.HTTPError as error:
        body = error.read().decode('utf-8', 'replace')
        code = (re.search(r'"error_code"\s*:\s*"([A-Z_]+)"', body) or [None, ''])[1]
        if step == 'summary' and code == 'HOST_NOT_LOADED':
            return None  # access is granted; Yandex just has no statistics for the site yet
        return f'Яндекс ответил {error.code} {code} на шаге {step}'
    except StopIteration:
        return 'в этом аккаунте Яндекс Вебмастера нет www.fluxixo.shop'
    except (urllib.error.URLError, KeyError, ValueError) as error:
        return f'{type(error).__name__} на шаге {step}'


def yandex_ok(token):
    return yandex_check(token) is None


def _is_existing_file(text):
    try:
        return Path(text).is_file()
    except OSError:
        return False


def _load_or_save_secret(provided, dpapi_name, label):
    if provided == 'PROMPT':
        val = clean_token(getpass.getpass(f'  Вставьте ключ {label} (символы не видны): '))
        if not val:
            raise SystemExit(f'  {label}: пустой ключ, ничего не сохранено.')
        save_credential(dpapi_name, val)
    elif provided:
        raw = Path(provided).read_text(encoding='utf-8') if _is_existing_file(provided) else provided
        val = clean_token(raw)
        if not val:
            raise SystemExit(f'  {label}: пустой ключ, ничего не сохранено.')
        save_credential(dpapi_name, val)
    return load_credential(dpapi_name)


def sync_worker_secrets(worker_items, *, requested=False, strict=False):
    """Best-effort (or strict under --worker-only) sync of secrets to Cloudflare Worker `fluxixo-autopilot`."""
    if not worker_items and not requested and not strict:
        return 0
    if not WORKER_DIR.is_dir():
        msg = f'  Cloudflare Worker ({WORKER_NAME}): каталог {WORKER_DIR} не найден.'
        if strict:
            raise SystemExit(msg)
        say(msg + ' Синхронизация Worker пропущена.')
        return 0
    wrangler_cmd = resolve_wrangler_cmd()
    if not wrangler_cmd:
        msg = f'  Cloudflare Worker ({WORKER_NAME}): wrangler CLI не найден.'
        if strict:
            raise SystemExit(msg)
        if requested or worker_items:
            say(msg + ' Секреты Worker пропущены (GitHub Secrets обновлены).')
        return 0
    if not wrangler_ready(wrangler_cmd):
        msg = f'  Cloudflare Worker ({WORKER_NAME}): wrangler не авторизован (выполните npx wrangler login).'
        if strict:
            raise SystemExit(msg)
        say(msg + ' Синхронизация Worker пропущена (GitHub Secrets обновлены).')
        return 0
    if not worker_items:
        say(f'  Cloudflare Worker ({WORKER_NAME}): нет сохранённых секретов для отправки.')
        return 0
    synced = 0
    for name, value in worker_items:
        try:
            put_worker_secret(wrangler_cmd, name, value)
            synced += 1
        except RuntimeError as exc:
            msg = f'  Cloudflare Worker ({WORKER_NAME}): ошибка сохранения {name}: {exc}'
            if strict:
                raise SystemExit(msg)
            say(msg)
    return synced


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--yandex', action='store_true', help='ask for a new Yandex OAuth token')
    parser.add_argument('--google-json', help='path to the downloaded Google service-account JSON key')
    parser.add_argument('--gemini-key', nargs='?', const='PROMPT', help='save Google Gemini API key')
    parser.add_argument('--gemini-image-key', nargs='?', const='PROMPT', help='save dedicated Google Nano Banana image API key')
    parser.add_argument('--gemini-text-key', nargs='?', const='PROMPT', help='save Google AI Studio text/Argon API key')
    parser.add_argument('--groq-key', nargs='?', const='PROMPT', help='save free Groq API key')
    parser.add_argument('--openrouter-key', nargs='?', const='PROMPT', help='save free OpenRouter API key')
    parser.add_argument('--github-dispatch-token', nargs='?', const='PROMPT',
                        help='save GitHub workflow_dispatch PAT for Cloudflare Worker (GITHUB_DISPATCH_TOKEN)')
    parser.add_argument('--autopilot-token', nargs='?', const='PROMPT',
                        help='save shared Autopilot sync token (AUTOPILOT_SYNC_TOKEN)')
    parser.add_argument('--sync-worker', action='store_true',
                        help='sync Google AI Studio and Autopilot secrets to Cloudflare Worker (fluxixo-autopilot)')
    parser.add_argument('--worker-only', action='store_true',
                        help='sync Worker secrets only via Wrangler (skip GitHub login and gh secret set)')
    args = parser.parse_args()
    say(f'FLUXIXO: ключи для автоматизации ({__import__("datetime").datetime.now():%Y-%m-%d %H:%M})')

    if not args.worker_only:
        login()

        key = load_credential('seo-data-key.dpapi')
        if not key:
            from cryptography.fernet import Fernet
            key = Fernet.generate_key().decode()
            save_credential('seo-data-key.dpapi', key)
        put('SEO_DATA_KEY', key)

        bing = load_credential('bing-api-key.dpapi')
        if bing:
            put('BING_WEBMASTER_API_KEY', bing)
        else:
            say('  Bing: ключа на этом компьютере нет (Bing Webmaster → Настройки → API access → API key).')

        if args.yandex:
            # The token is taken from the clipboard (the owner pressed "copy" on the Yandex page); typing is the fallback.
            # Copying the command from the chat replaces the clipboard, so the program waits for the token to be copied.
            def clipboard_token():
                clip = subprocess.run(['powershell', '-NoProfile', '-Command', 'Get-Clipboard'], stdout=subprocess.PIPE,
                                      stderr=subprocess.DEVNULL).stdout.decode('utf-8', 'replace').strip()
                return clean_token(clip) if len(clip) >= 30 and ' ' not in clip and '\n' not in clip else ''
            token = clipboard_token()
            if not token:
                say('  Яндекс: теперь в браузере нажмите кнопку копирования рядом с токеном. Жду до 5 минут...')
                deadline = time.time() + 300
                while not token and time.time() < deadline:
                    time.sleep(1.5)
                    token = clipboard_token()
            if token:
                say('  Яндекс: токен взят из буфера обмена.')
            else:
                token = clean_token(getpass.getpass('  Вставьте новый токен Яндекса (символы не видны) и нажмите Enter: '))
            problem = yandex_check(token)
            if problem:
                raise SystemExit(f'  Токен не подошёл: {problem}. Ничего не сохранено.')
            save_credential('yandex-oauth-token.dpapi', token)
        token = load_credential('yandex-oauth-token.dpapi')
        if token and yandex_ok(token):
            put('YANDEX_WEBMASTER_TOKEN', token)
        else:
            say('  Яндекс: у текущего токена нет права webmaster:hostinfo. Получите новый и запустите с --yandex.')

        if args.google_json:
            text = Path(args.google_json).read_text(encoding='utf-8')
            info = json.loads(text)
            if info.get('type') != 'service_account' or not info.get('private_key') or not info.get('client_email'):
                raise SystemExit('  Это не ключ служебного аккаунта Google (JSON).')
            save_credential('gsc-service-account.dpapi', text)
            put('GSC_SERVICE_ACCOUNT_JSON', text)
            say(f'  Google: добавьте {info["client_email"]} в Search Console → Настройки → Пользователи (полный доступ).')

    secret_specs = (
        ('gemini_key', 'gemini-api-key.dpapi', 'GEMINI_API_KEY', 'GEMINI_API_KEY',
         'Google Gemini API (aistudio.google.com/apikey)'),
        ('gemini_image_key', 'gemini-image-api-key.dpapi', 'GEMINI_IMAGE_API_KEY', 'GEMINI_IMAGE_API_KEY',
         'Google Nano Banana Image API (aistudio.google.com/apikey)'),
        ('gemini_text_key', 'gemini-text-api-key.dpapi', 'GEMINI_TEXT_API_KEY', 'GEMINI_TEXT_API_KEY',
         'Google AI Studio Text / Argon API (aistudio.google.com/apikey)'),
        ('groq_key', 'groq-api-key.dpapi', 'GROQ_API_KEY', None,
         'Groq API (console.groq.com/keys)'),
        ('openrouter_key', 'openrouter-api-key.dpapi', 'OPENROUTER_API_KEY', None,
         'OpenRouter API (openrouter.ai/keys)'),
        ('github_dispatch_token', 'github-dispatch-token.dpapi', None, 'GITHUB_DISPATCH_TOKEN',
         'GitHub workflow_dispatch PAT (github.com/settings/tokens)'),
        ('autopilot_token', 'autopilot-sync-token.dpapi', 'AUTOPILOT_SYNC_TOKEN', 'AUTOPILOT_SYNC_TOKEN',
         'FLUXIXO Autopilot Sync Token'),
    )
    worker_items = []
    for arg_attr, dpapi_name, gh_secret, worker_secret, label in secret_specs:
        existing = _load_or_save_secret(getattr(args, arg_attr), dpapi_name, label)
        if existing:
            if gh_secret and not args.worker_only:
                put(gh_secret, existing)
            if worker_secret:
                worker_items.append((worker_secret, existing))

    sync_worker_secrets(worker_items, requested=args.sync_worker, strict=args.worker_only)
    if args.worker_only:
        say(f'Готово. Секреты Cloudflare Worker ({WORKER_NAME}) обновлены.')
    else:
        say('Готово. Задание на GitHub и доступные секреты Worker обновлены.')


if __name__ == '__main__':
    pause = '--pause' in sys.argv
    if pause:
        sys.argv.remove('--pause')
    exit_code = 0
    try:
        main()
    except SystemExit as stop:
        if stop.code not in (None, 0):
            say(str(stop.code))
            exit_code = stop.code if isinstance(stop.code, int) else 1
    except Exception as error:  # shown and logged, so the window never just vanishes
        say(f'Ошибка: {type(error).__name__}: {error}')
        exit_code = 1
    finally:
        if pause:
            input('\nНажмите Enter, чтобы закрыть окно.')
    if exit_code:
        sys.exit(exit_code)
