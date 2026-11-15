"""Store the AliExpress Open Platform App Key and App Secret on this PC, encrypted for this Windows user (DPAPI).

Run by double-clicking "FLUXIXO ключи AliExpress.cmd" on the Desktop. The values are typed into this window only:
nothing is printed, sent anywhere or written in plain text. They let the local daily run find products and make
affiliate links without GitHub (owner, 2026-11-14).
"""
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dpapi_store import load_credential, save_credential  # noqa: E402

FILES = (('App Key', 'ali-app-key.dpapi'), ('App Secret', 'ali-app-secret.dpapi'))


def main():
    print('FLUXIXO: ключи AliExpress API (App Key и App Secret)')
    print('Где взять: https://openservice.aliexpress.com -> App Management -> ваше приложение.')
    print('Вставьте значение (правой кнопкой мыши или Ctrl+V) и нажмите Enter. Символы на экране не видны - так и задумано.\n')
    for label, filename in FILES:
        current = load_credential(filename)
        hint = ' (уже сохранён; Enter - оставить как есть)' if current else ''
        value = getpass.getpass(f'{label}{hint}: ').strip()
        if not value and current:
            print(f'  {label}: оставлен прежний.')
            continue
        if len(value) < 6:
            print(f'  {label}: слишком короткое значение, ничего не сохранено. Запустите ещё раз.')
            return 1
        save_credential(filename, value)
        print(f'  {label}: сохранён ({len(value)} символов).')
    print('\nГотово. Можно закрыть это окно и написать в чат: "ключи готовы".')
    return 0


if __name__ == '__main__':
    code = main()
    input('\nНажмите Enter, чтобы закрыть окно...')
    sys.exit(code)
