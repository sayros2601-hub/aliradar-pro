"""One-time setup, run by the site owner on this PC: puts the search-console keys into GitHub secrets.

The daily GitHub job (.github/workflows/fluxixo_seo_daily.yml) reads them from there. Keys never pass through chat:
this script takes them from the encrypted store in .local/ (or asks for them without echo) and hands them to
`gh secret set` through standard input.

  python fluxixo_site/tools/seo_setup_secrets.py                      Bing key + data key (already on this PC)
  python fluxixo_site/tools/seo_setup_secrets.py --yandex             also asks for a new Yandex token
  python fluxixo_site/tools/seo_setup_secrets.py --google-json FILE   also adds the Google service-account key
"""
import argparse
import getpass
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dpapi_store import load_credential, save_credential  # noqa: E402

REPO = 'sayros2601-hub/aliradar-pro'
LOG = Path(__file__).resolve().parents[2] / '.local/seo-setup-log.txt'


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


def put(name, value):
    result = subprocess.run(['gh', 'secret', 'set', name, '--repo', REPO], input=value.encode('utf-8'),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise SystemExit(f'gh secret set {name} failed: {result.stderr.decode("utf-8", "replace").strip()}')
    say(f'  {name}: сохранён в GitHub')


def clean_token(text):
    """Pasting into a terminal can wrap the text in bracketed-paste codes or add spaces; keep only token characters."""
    text = re.sub(r'\x1b\[20[01]~', '', text or '')
    return ''.join(ch for ch in text if ch.isalnum() or ch in '_-.')


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--yandex', action='store_true', help='ask for a new Yandex OAuth token')
    parser.add_argument('--google-json', help='path to the downloaded Google service-account JSON key')
    parser.add_argument('--gemini-key', nargs='?', const='PROMPT', help='save free Google Gemini API key')
    parser.add_argument('--groq-key', nargs='?', const='PROMPT', help='save free Groq API key')
    parser.add_argument('--openrouter-key', nargs='?', const='PROMPT', help='save free OpenRouter API key')
    args = parser.parse_args()
    say(f'FLUXIXO: ключи для ежедневного SEO-задания ({__import__("datetime").datetime.now():%Y-%m-%d %H:%M})')
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

    ai_specs = (
        ('gemini', args.gemini_key, 'gemini-api-key.dpapi', 'GEMINI_API_KEY', 'Google Gemini API (aistudio.google.com/apikey)'),
        ('groq', args.groq_key, 'groq-api-key.dpapi', 'GROQ_API_KEY', 'Groq API (console.groq.com/keys)'),
        ('openrouter', args.openrouter_key, 'openrouter-api-key.dpapi', 'OPENROUTER_API_KEY', 'OpenRouter API (openrouter.ai/keys)'),
    )
    for _, provided, dpapi_name, gh_secret, label in ai_specs:
        if provided == 'PROMPT':
            val = clean_token(getpass.getpass(f'  Вставьте ключ {label} (символы не видны): '))
            if not val:
                raise SystemExit(f'  {gh_secret}: пустой ключ, ничего не сохранено.')
            save_credential(dpapi_name, val)
        elif provided:
            p = Path(provided)
            val = clean_token(p.read_text(encoding='utf-8')) if p.is_file() else clean_token(provided)
            save_credential(dpapi_name, val)
        existing = load_credential(dpapi_name)
        if existing:
            put(gh_secret, existing)
    say('Готово. Задание на GitHub подхватит ключи при следующем запуске.')


if __name__ == '__main__':
    pause = '--pause' in sys.argv
    if pause:
        sys.argv.remove('--pause')
    try:
        main()
    except SystemExit as stop:
        if stop.code not in (None, 0):
            say(str(stop.code))
    except Exception as error:  # shown and logged, so the window never just vanishes
        say(f'Ошибка: {type(error).__name__}: {error}')
    finally:
        if pause:
            input('\nНажмите Enter, чтобы закрыть окно.')
