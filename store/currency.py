"""Display currency only; inventory prices remain in INR."""
import json
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache

from babel import Locale
from babel.numbers import get_territory_currencies, get_currency_precision, format_decimal
from django.conf import settings


@lru_cache(maxsize=1)
def countries():
    excluded = {'ZZ', 'EU', 'EZ', 'UN', 'QO', 'XA', 'XB'}
    return sorted([
        {'code': code, 'name': name, 'currency': (get_territory_currencies(code) or ['USD'])[0]}
        for code, name in Locale('en').territories.items()
        if len(code) == 2 and code not in excluded
    ], key=lambda row: row['name'])


def rate_path():
    return settings.BASE_DIR / '.local/exchange-rates.json'


def rates():
    try:
        data = json.loads(rate_path().read_text())
        validate_rates(data)
        return data
    except (OSError, ValueError, KeyError, TypeError, ArithmeticError):
        return {'rates': {'INR': 1}, 'time_last_update_unix': None}


def validate_rates(data):
    if data.get('result') != 'success' or data.get('base_code') != 'INR':
        raise ValueError('Expected successful INR rates.')
    if Decimal(str(data['rates']['INR'])) != 1:
        raise ValueError('Invalid base rate.')
    for code, value in data['rates'].items():
        rate = Decimal(str(value))
        if not rate.is_finite() or rate <= 0:
            raise ValueError('Exchange rates must be positive finite numbers.')
    datetime.fromtimestamp(data['time_last_update_unix'], timezone.utc)


def market(request):
    if hasattr(request, '_astrol_market'):
        return request._astrol_market
    country = next((c for c in countries() if c['code'] == request.COOKIES.get('astrol_country', 'IN')), None)
    country = country or next(c for c in countries() if c['code'] == 'IN')
    data = rates()
    code = country['currency']
    fallback = code not in data['rates']
    if fallback:
        code = 'USD' if 'USD' in data['rates'] else 'INR'
    stamp = data['time_last_update_unix']
    result = {**country, 'currency': code, 'rate': Decimal(str(data['rates'][code])),
              'digits': get_currency_precision(code), 'fallback': fallback,
              'date': datetime.fromtimestamp(stamp, timezone.utc).date() if stamp else None,
              'stale': bool(stamp and datetime.now(timezone.utc).timestamp() - stamp > 3 * 86400)}
    request._astrol_market = result
    return result


def convert(value, current):
    return (Decimal(str(value)) * current['rate']).quantize(Decimal(10) ** -current['digits'], rounding=ROUND_HALF_UP)


def format_money(value, current, converted=False):
    amount = Decimal(str(value)) if converted else convert(value, current)
    pattern = '#,##,##0' if current['currency'] == 'INR' else '#,##0'
    if current['digits']:
        pattern += '.' + '0' * current['digits']
    number = format_decimal(amount, format=pattern, locale='en_IN' if current['currency'] == 'INR' else 'en_US')
    return ('₹ ' if current['currency'] == 'INR' else current['currency'] + ' ') + number


def currency_context(request):
    return {'market': market(request), 'market_countries': countries()}
