"""Cache a dated public currency snapshot; never invent rates on network failure."""
from datetime import datetime, timezone
import json
import math
import urllib.request
from dealvault_core import DATA_DIR, read_json, write_json

RATES_FILE = DATA_DIR / 'exchange_rates.json'


def update_rates():
    try:
        req=urllib.request.Request('https://open.er-api.com/v6/latest/USD',headers={'User-Agent':'DealVault/2026.10'})
        with urllib.request.urlopen(req,timeout=12) as response:
            data=json.load(response)
        if data.get('result') != 'success' or data.get('base_code') != 'USD':
            raise ValueError('Unexpected exchange-rate response')
        rates={currency:float(data['rates'][currency]) for currency in ('USD','ILS','EUR','RUB')}
        if rates['USD'] != 1 or any(not math.isfinite(rate) or not 0 < rate < 100000 for rate in rates.values()):
            raise ValueError('Invalid exchange rates')
        snapshot={'source':'https://open.er-api.com/v6/latest/USD',
                  'observed_at':datetime.fromtimestamp(data['time_last_update_unix'],timezone.utc).isoformat(),
                  'rates':rates}
        write_json(RATES_FILE,snapshot)
        print('[Rates] Stored dated USD/ILS/EUR/RUB snapshot:',snapshot['observed_at'])
        return snapshot
    except (OSError,ValueError,KeyError,TypeError) as error:
        previous=read_json(RATES_FILE,{'rates':{'USD':1},'observed_at':None})
        print('[Rates] Network/schema unavailable; preserving previous snapshot or USD only.')
        return previous


if __name__ == '__main__':
    update_rates()
