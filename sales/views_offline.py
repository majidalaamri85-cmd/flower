import json
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from inventory.models import Product, StockMovement

from .models import BundleOffer, Customer, OfflineSaleQueue, Sale, SaleItem


@login_required
@csrf_exempt
def sync_offline_sales(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON payload'}, status=400)

    offline_sales = data.get('sales', [])
    synced_count = 0
    errors = []

    for sale_data in offline_sales:
        try:
            with transaction.atomic():
                customer = None
                if sale_data.get('customer_id'):
                    customer = Customer.objects.filter(id=sale_data['customer_id']).first()

                sale = Sale.objects.create(
                    customer=customer,
                    employee=request.user,
                    subtotal=Decimal(str(sale_data['subtotal'])),
                    discount=Decimal(str(sale_data.get('discount', 0))),
                    tax=Decimal(str(sale_data.get('tax', 0))),
                    total=Decimal(str(sale_data['total'])),
                    payment_method=sale_data.get('payment_method', 'cash'),
                    paid_amount=Decimal(str(sale_data['paid_amount'])),
                    notes=f"[تمت دون اتصال] {sale_data.get('notes', '')}".strip(),
                    is_delivery=bool(sale_data.get('is_delivery', False)),
                    delivery_address=sale_data.get('delivery_address', ''),
                )

                for item in sale_data.get('items', []):
                    product = Product.objects.get(id=item['product_id'])
                    quantity = Decimal(str(item['quantity']))
                    unit_price = Decimal(str(item['unit_price']))

                    SaleItem.objects.create(
                        sale=sale,
                        product=product,
                        quantity=quantity,
                        unit_price=unit_price,
                        total=quantity * unit_price,
                    )

                    StockMovement.objects.create(
                        product=product,
                        quantity=quantity,
                        movement_type='out',
                        reference=f"OFFLINE-{sale.invoice_number}",
                        notes=f"مبيعات دون اتصال - {sale_data.get('timestamp', '')}",
                        created_by=request.user,
                    )

                OfflineSaleQueue.objects.create(
                    sale_data=sale_data,
                    synced_at=timezone.now(),
                    is_synced=True,
                )
                synced_count += 1
        except Exception as exc:
            OfflineSaleQueue.objects.create(
                sale_data=sale_data,
                is_synced=False,
                sync_attempts=1,
            )
            errors.append({'error': str(exc), 'sale': sale_data})

    return JsonResponse({'success': True, 'synced_count': synced_count, 'errors': errors})


@login_required
def get_offline_data(request):
    products = Product.objects.filter(is_active=True, quantity__gt=0).order_by('name')
    products_data = [
        {
            'id': product.id,
            'name': product.name,
            'type': product.type,
            'selling_price': str(product.selling_price),
            'quantity': float(product.quantity),
            'image_url': product.image.url if product.image else None,
        }
        for product in products
    ]

    customers = Customer.objects.filter(is_vip=True).order_by('-total_purchases')[:100]
    customers_data = [{'id': customer.id, 'name': customer.name, 'phone': customer.phone} for customer in customers]

    today = timezone.localdate()
    bundles = BundleOffer.objects.filter(is_active=True, start_date__lte=today, end_date__gte=today)
    bundles_data = [
        {
            'id': bundle.id,
            'name': bundle.name,
            'bundle_price': str(bundle.bundle_price),
            'regular_price': str(bundle.regular_price),
            'flower_product_id': bundle.flower_product_id,
            'chocolate_product_id': bundle.chocolate_product_id,
        }
        for bundle in bundles
    ]

    return JsonResponse(
        {
            'success': True,
            'products': products_data,
            'customers': customers_data,
            'bundles': bundles_data,
            'sync_time': timezone.now().isoformat(),
        }
    )