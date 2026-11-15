"""A small window to store the AliExpress Open Platform App Key and App Secret on this PC (encrypted with DPAPI).

The values never leave the window except into the encrypted files .local/ali-app-key.dpapi and
.local/ali-app-secret.dpapi; nothing is printed or sent anywhere.
"""
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dpapi_store import load_credential, save_credential  # noqa: E402


def main():
    root = tk.Tk()
    root.title('FLUXIXO — ключи AliExpress API')
    root.attributes('-topmost', True)
    root.resizable(False, False)
    pad = {'padx': 14, 'pady': 6}
    tk.Label(root, text='Ключи AliExpress API для сайта FLUXIXO', font=('Segoe UI', 12, 'bold')).grid(row=0, column=0, columnspan=2, **pad)
    tk.Label(root, text='Где взять: openservice.aliexpress.com → App Management → ваше приложение\n'
                        '(те же App Key и App Secret, что были в GitHub).', justify='left').grid(row=1, column=0, columnspan=2, sticky='w', **pad)
    tk.Label(root, text='App Key:').grid(row=2, column=0, sticky='e', **pad)
    key = tk.Entry(root, width=46)
    key.grid(row=2, column=1, **pad)
    tk.Label(root, text='App Secret:').grid(row=3, column=0, sticky='e', **pad)
    secret = tk.Entry(root, width=46, show='•')
    secret.grid(row=3, column=1, **pad)
    shown = tk.BooleanVar(value=False)
    tk.Checkbutton(root, text='показать App Secret', variable=shown,
                   command=lambda: secret.config(show='' if shown.get() else '•')).grid(row=4, column=1, sticky='w', padx=14)
    if load_credential('ali-app-key.dpapi'):
        tk.Label(root, text='Ключи уже сохранены раньше; новые значения их заменят.', fg='#666').grid(row=5, column=0, columnspan=2, **pad)

    def save():
        k, s = key.get().strip(), secret.get().strip()
        if len(k) < 6 or len(s) < 10:
            messagebox.showwarning('FLUXIXO', 'Вставьте оба значения целиком: App Key и App Secret.', parent=root)
            return
        save_credential('ali-app-key.dpapi', k)
        save_credential('ali-app-secret.dpapi', s)
        messagebox.showinfo('FLUXIXO', 'Ключи сохранены на этом компьютере в зашифрованном виде.\nМожно вернуться в чат.', parent=root)
        root.destroy()

    tk.Button(root, text='Сохранить', width=16, command=save, bg='#e4007c', fg='white').grid(row=6, column=0, columnspan=2, pady=12)
    key.focus_set()
    root.mainloop()


if __name__ == '__main__':
    main()
