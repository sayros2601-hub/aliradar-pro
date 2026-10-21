"""Private owner report. Missing measurements remain unknown, never invented zeros."""
import argparse
from datetime import date, datetime, timezone
from html import escape
from pathlib import Path
from dealvault_core import BASE_DIR, DATA_DIR, read_json, write_json, utc_now

PRIVATE = BASE_DIR / '.local' / 'business'
METRICS = ('visits', 'partner_clicks', 'orders', 'approved_commission', 'paid_commission', 'ad_spend', 'other_costs')


def analyse_periods(records):
    """One non-overlapping USD period per observation; all amounts are aggregate only."""
    if not isinstance(records, list):
        raise ValueError('Periods must be a list')
    results = []
    previous_end = None
    for record in sorted(records, key=lambda r: r.get('start', '') if isinstance(r, dict) else ''):
        if not isinstance(record, dict):raise ValueError('Invalid period')
        start, end = date.fromisoformat(record['start']), date.fromisoformat(record['end'])
        if start > end or end > datetime.now(timezone.utc).date() or (previous_end and start <= previous_end):
            raise ValueError('Periods must be past/current, ordered and non-overlapping')
        previous_end = end
        if record.get('currency') != 'USD':raise ValueError('Use USD consistently; do not mix currencies')
        values = {}
        for key in METRICS:
            value = record.get(key)
            from product_selection import number
            if value is not None and not number(value):raise ValueError(f'Invalid {key}')
            if value is not None and not (record.get('evidence') or {}).get(key):
                raise ValueError(f'{key} needs a report reference; zero also needs evidence')
            if key in ('visits', 'partner_clicks', 'orders') and value is not None and int(value) != value:
                raise ValueError(f'{key} must be a count')
            values[key] = value
        # Portal click totals can include other channels. Do not label this a site conversion rate.
        paid, ads, costs = (values[k] for k in ('paid_commission','ad_spend','other_costs'))
        cash = paid - ads - costs if all(v is not None for v in (paid, ads, costs)) else None
        clicks, approved = values['partner_clicks'], values['approved_commission']
        epc = approved / clicks if clicks and approved is not None and record.get('attribution_scope') == 'matched_cohort' else None
        results.append({'start':str(start),'end':str(end),**values,'cash_after_recorded_costs':cash,
                        'approved_epc':epc,'note':'Cash result before tax and owner time; EPC only for a matched attribution cohort.'})
    return results


def build_report(directory=None):
    directory = Path(directory or PRIVATE)
    directory.mkdir(parents=True, exist_ok=True)
    ledger = read_json(directory/'periods.json', {'periods':[]})
    periods = analyse_periods(ledger['periods'])
    catalog = read_json(DATA_DIR/'products.json')['products']
    selection = read_json(DATA_DIR/'selection_report.json', {})
    links = read_json(DATA_DIR/'link_health_report.json', {})
    rates = read_json(DATA_DIR/'exchange_rates.json', {})
    report = {'generated_at':utc_now(),'active_products':len(catalog),
              'eligible_new_candidates':selection.get('eligible'),
              'selection_checked_at':selection.get('checked_at'),
              'link_summary':links.get('summary'), 'rates_observed_at':rates.get('observed_at'),
              'periods':periods,'revenue_status':'reported' if periods else 'not_measured',
              'limitations':['A successful scheduled build is not proof of new products or buyers.',
                             'Live AliExpress collection and account payout eligibility are unverified.',
                             'Country selection is a delivery reminder, not a localized inventory filter.',
                             'Public ad libraries do not reveal every advertisement seen by a person.',
                             'Analytics visits and affiliate sales require separate reports and matching scope.']}
    write_json(directory/'health.json', report)
    labels = {'visits':'Посещения','partner_clicks':'Переходы в отчёте партнёрки','orders':'Заказы в отчёте',
              'approved_commission':'Подтверждённая комиссия, USD','paid_commission':'Получено, USD',
              'ad_spend':'Реклама, USD','other_costs':'Остальные расходы, USD',
              'cash_after_recorded_costs':'Остаток после учтённых расходов, до налогов', 'approved_epc':'Комиссия на клик: только сопоставимая группа'}
    latest = periods[-1] if periods else {}
    rows = ''.join(f'<tr><th>{escape(label)}</th><td>{escape(str(latest.get(key))) if latest.get(key) is not None else "Нет подтверждённых данных"}</td></tr>' for key,label in labels.items())
    document = f'''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>DealVault — состояние бизнеса</title>
<style>body{{font:16px/1.6 system-ui;max-width:960px;margin:40px auto;padding:24px;background:#f5f7fb;color:#172332}}section{{background:white;border-radius:18px;padding:24px;margin:20px 0}}table{{width:100%;border-collapse:collapse}}th,td{{padding:12px;text-align:left;border-bottom:1px solid #dde3ec}}a{{color:#2459eb}}small{{color:#526172}}</style>
<h1>DealVault: что работает и что приносит деньги</h1><p>Личный отчёт на компьютере. Он не публикуется на сайте и не содержит придуманных показателей.</p>
<section><h2>Техническое состояние</h2><p>В каталоге: {len(catalog)}. Прошли отбор для добавления: {selection.get('eligible','неизвестно')}.</p><p>Ежедневная сборка обновляет проверенные файлы. Новые товары появятся только после получения и проверки новых данных.</p><p>Последняя проверка отбора: {escape(str(selection.get('checked_at','нет данных')))}. Курс валют: {escape(str(rates.get('observed_at','нет данных')))}.</p><p><a href="https://github.com/sayros2601-hub/aliradar-pro/actions">Проверить публикации</a> · <a href="https://dealvault.pages.dev/">Открыть сайт</a> · <a href="https://search.google.com/search-console">Google Search Console</a> · <a href="https://dash.cloudflare.com/">Cloudflare</a></p></section>
<section><h2>Деньги и измерения</h2><table>{rows}</table><p>Заказ, ожидаемая комиссия, подтверждённая комиссия и выплата — разные события. Посещения Cloudflare и переходы из кабинета партнёрки могут иметь разные источники и периоды. Без совпадения нельзя считать конверсию сайта.</p></section>
<section><h2>Следующее действие</h2><ol><li>Проверить статус участия, выплаты и принадлежность ссылок в кабинете партнёрской программы. Рабочая ссылка не доказывает зачисление комиссии.</li><li>Проверить данные Google и Cloudflare после накопления наблюдений. Тестовые посещения не считать спросом.</li><li>Выбрать одну страну и одну бытовую задачу. Подготовить полезное сравнение вариантов с ограничениями; публиковать только в разрешённом собственном канале.</li><li>Сопоставить источники, переходы и подтверждённую комиссию. Не покупать рекламу по неподтверждённым цифрам.</li><li>Вкладывать часть фактически полученных денег в измеримое ограничение: качественный контент или домен. Платный хостинг нужен при реальном недостатке текущего.</li></ol></section>
<section><h2>Границы автоматизации</h2><p>Свежий сбор AliExpress не подтверждён. Рекламные библиотеки не показывают всю рекламу страны. Выбор страны на сайте — напоминание о доставке, а не проверка ассортимента. Отключение фильтра бесплатной доставки сохранено.</p><p>Не настроены подтверждённые данные о выплатах и адрес редакции. Рост и прибыль не гарантированы; мы проверяем конкретные гипотезы.</p></section><small>Сформировано: {escape(report['generated_at'])}</small></html>'''
    (directory/'dashboard.html').write_text(document, encoding='utf-8')
    if not (directory/'periods.json').exists():write_json(directory/'periods.json', {'periods':[]})
    print('[Business] Private report generated. Unmeasured revenue remains unknown.')
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    build_report(parser.parse_args().output)
