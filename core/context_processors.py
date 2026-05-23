from types import SimpleNamespace

from decouple import config

from .models import ShopSettings


def shop_settings(request):
    record = ShopSettings.objects.first()
    if record:
        if not getattr(record, 'currency_symbol', ''):
            record.currency_symbol = 'ر.ع'
        return {'settings': record}

    fallback = SimpleNamespace(
        shop_name=config('SHOP_NAME', default='ROOTS FLOWERS'),
        phone=config('SHOP_PHONE', default=''),
        email=config('SHOP_EMAIL', default=''),
        address=config('SHOP_ADDRESS', default=''),
        currency_symbol=config('CURRENCY_SYMBOL', default='ر.ع'),
    )
    return {'settings': fallback}
