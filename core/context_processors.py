from types import SimpleNamespace

from decouple import config

from .models import ShopSettings


def shop_settings(request):
    record = ShopSettings.objects.first()
    if record:
        return {'settings': record}

    fallback = SimpleNamespace(
        shop_name=config('SHOP_NAME', default='ROOTS FLOWERS'),
        phone=config('SHOP_PHONE', default=''),
        email=config('SHOP_EMAIL', default=''),
        address=config('SHOP_ADDRESS', default=''),
    )
    return {'settings': fallback}