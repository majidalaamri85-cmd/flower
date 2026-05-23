import json
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone

from inventory.models import Product, StockMovement

from .models import BundleOffer, Customer, OfflineSaleQueue, Sale, SaleItem


def _decimal(value):
    return Decimal(str(value))


@login_required
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
        client_sale_id = str(sale_data.get('client_sale_id') or '').strip() or None
        try:
            with transaction.atomic():
                if client_sale_id and OfflineSaleQueue.objects.filter(client_sale_id=client_sale_id, is_synced=True).exists():
                    synced_count += 1
                    continue

                items = sale_data.get('items') or []
                if not items:
                    raise ValueError('Sale must contain at least one item')

                subtotal = _decimal(sale_data['subtotal'])
                discount = _decimal(sale_data.get('discount', 0))
                tax = _decimal(sale_data.get('tax', 0))
                total = _decimal(sale_data['total'])
                paid_amount = _decimal(sale_data['paid_amount'])
                if min(subtotal, discount, tax, total, paid_amount) < 0:
                    raise ValueError('Amounts cannot be negative')
                if subtotal - discount + tax != total:
                    raise ValueError('Sale totals do not match')
                if paid_amount < total:
                    raise ValueError('Paid amount is less than total')

                customer = None
                if sale_data.get('customer_id'):
                    customer = Customer.objects.filter(id=sale_data['customer_id']).first()

                sale = Sale.objects.create(
                    customer=customer,
                    employee=request.user,
                    subtotal=subtotal,
                    discount=discount,
                    tax=tax,
                    total=total,
                    payment_method=sale_data.get('payment_method', 'cash'),
                    paid_amount=paid_amount,
                    notes=f"[offline] {sale_data.get('notes', '')}".strip(),
                    is_delivery=bool(sale_data.get('is_delivery', False)),
                    delivery_address=sale_data.get('delivery_address', ''),
                )

                line_total = Decimal('0')
                for item in items:
                    product = Product.objects.select_for_update().get(id=item['product_id'], is_active=True)
                    quantity = _decimal(item['quantity'])
                    unit_price = _decimal(item['unit_price'])
                    if quantity <= 0 or unit_price < 0:
                        raise ValueError('Item quantity and price must be valid')
                    if quantity > product.quantity:
                        raise ValueError(f'Insufficient stock for product {product.id}')

                    line_total += quantity * unit_price
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
                        notes=f"Offline sale - {sale_data.get('timestamp', '')}",
                        created_by=request.user,
                    )

                if line_total != subtotal:
                    raise ValueError('Item totals do not match sale subtotal')

                OfflineSaleQueue.objects.create(
                    client_sale_id=client_sale_id,
                    sale_data=sale_data,
                    synced_at=timezone.now(),
                    is_synced=True,
                )
                if customer:
                    customer.total_purchases += total
                    customer.last_purchase_date = timezone.now()
                    customer.save(update_fields=['total_purchases', 'last_purchase_date'])
                synced_count += 1
        except (InvalidOperation, KeyError, Product.DoesNotExist, ValueError) as exc:
            defaults = {
                'sale_data': sale_data,
                'is_synced': False,
                'sync_attempts': 1,
            }
            if client_sale_id:
                OfflineSaleQueue.objects.update_or_create(client_sale_id=client_sale_id, defaults=defaults)
            else:
                OfflineSaleQueue.objects.create(**defaults)
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
