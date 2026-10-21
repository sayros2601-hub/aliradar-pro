"""Telegram drafts by default; --send opts into the owner's explicit channel."""
from social_posters import format_telegram_caption, send_telegram_deal, main

if __name__ == '__main__':
    main('telegram')
