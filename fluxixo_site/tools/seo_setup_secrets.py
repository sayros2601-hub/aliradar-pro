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
import subprocess
import sys
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


def yandex_ok(token):
    request = urllib.request.Request('https://api.webmaster.yandex.net/v4/user', headers={'Authorization': f'OAuth {token}'})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            user = json.loads(response.read())['user_id']
        hosts = urllib.request.Request(f'https://api.webmaster.yandex.net/v4/user/{user}/hosts',
                                       headers={'Authorization': f'OAuth {token}'})
        with urllib.request.urlopen(hosts, timeout=20) as response:
            host = next(h['host_id'] for h in json.loads(response.read())['hosts'] if 'www.fluxixo.shop' in h['host_id'])
        summary = urllib.request.Request(
            f'https://api.webmaster.yandex.net/v4/user/{user}/hosts/{urllib.request.quote(host, safe="")}/summary',
            headers={'Authorization': f'OAuth {token}'})
        with urllib.request.urlopen(summary, timeout=20):
            return True
    except (urllib.error.URLError, KeyError, StopIteration, ValueError):
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--yandex', action='store_true', help='ask for a new Yandex OAuth token')
    parser.add_argument('--google-json', help='path to the downloaded Google service-account JSON key')
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
        token = getpass.getpass('  Вставьте новый токен Яндекса (символы не видны) и нажмите Enter: ').strip()
        if not yandex_ok(token):
            raise SystemExit('  Токен не даёт доступа к статистике сайта (нужно право webmaster:hostinfo). Ничего не сохранено.')
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
