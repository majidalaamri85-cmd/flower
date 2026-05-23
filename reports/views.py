import json
from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import render
from django.utils import timezone

from accounts.models import Expense
from inventory.models import Product, StockMovement
from sales.models import Sale, SaleItem


def _percent_change(current, previous):
	current = float(current or 0)
	previous = float(previous or 0)
	if previous == 0:
		return 100 if current > 0 else 0
	return ((current - previous) / previous) * 100


def _trend_label(change):
	if change > 5:
		return 'صاعد'
	if change < -5:
		return 'هابط'
	return 'مستقر'


@login_required
def daily_report(request):
	today = timezone.localdate()
	selected_date = request.GET.get('date', today.isoformat())
	try:
		selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
	except ValueError:
		selected_date = today

	start_of_day = timezone.make_aware(datetime.combine(selected_date, datetime.min.time()))
	end_of_day = timezone.make_aware(datetime.combine(selected_date, datetime.max.time()))

	sales = Sale.objects.filter(created_at__range=[start_of_day, end_of_day])
	total_sales = sales.aggregate(total=Sum('total'))['total'] or 0
	sales_count = sales.count()
	avg_sale = total_sales / sales_count if sales_count else 0

	payment_methods = sales.values('payment_method').annotate(total=Sum('total'), count=Count('id')).order_by('-total')
	expenses = Expense.objects.filter(expense_date=selected_date)
	total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0
	net_profit = total_sales - total_expenses

	top_products = (
		SaleItem.objects.filter(sale__created_at__range=[start_of_day, end_of_day])
		.values('product__name', 'product__type')
		.annotate(total_quantity=Sum('quantity'), total_revenue=Sum('total'))
		.order_by('-total_revenue')[:10]
	)

	stock_in = StockMovement.objects.filter(created_at__range=[start_of_day, end_of_day], movement_type='in').aggregate(total=Sum('quantity'))['total'] or 0
	stock_out = StockMovement.objects.filter(created_at__range=[start_of_day, end_of_day], movement_type='out').aggregate(total=Sum('quantity'))['total'] or 0
	waste = StockMovement.objects.filter(created_at__range=[start_of_day, end_of_day], movement_type='waste').aggregate(total=Sum('quantity'))['total'] or 0

	return render(
		request,
		'reports/daily_report.html',
		{
			'selected_date': selected_date,
			'total_sales': total_sales,
			'sales_count': sales_count,
			'avg_sale': avg_sale,
			'payment_methods': payment_methods,
			'total_expenses': total_expenses,
			'net_profit': net_profit,
			'top_products': top_products,
			'stock_in': stock_in,
			'stock_out': stock_out,
			'waste': waste,
		},
	)


@login_required
def monthly_report(request):
	now = timezone.now()
	try:
		current_month = int(request.GET.get('month', now.month))
		current_year = int(request.GET.get('year', now.year))
	except (TypeError, ValueError):
		current_month = now.month
		current_year = now.year
	if current_month < 1 or current_month > 12:
		current_month = now.month

	start_date = datetime(current_year, current_month, 1)
	if current_month == 12:
		end_date = datetime(current_year + 1, 1, 1) - timedelta(seconds=1)
	else:
		end_date = datetime(current_year, current_month + 1, 1) - timedelta(seconds=1)

	start_date_aware = timezone.make_aware(start_date)
	end_date_aware = timezone.make_aware(end_date)

	sales = Sale.objects.filter(created_at__range=[start_date_aware, end_date_aware])
	total_sales = sales.aggregate(total=Sum('total'))['total'] or 0
	sales_count = sales.count()

	daily_sales = []
	day = start_date_aware
	while day <= end_date_aware:
		day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)
		day_total = Sale.objects.filter(created_at__range=[day, day_end]).aggregate(total=Sum('total'))['total'] or 0
		daily_sales.append({'day': day.day, 'total': float(day_total)})
		day += timedelta(days=1)

	expenses = Expense.objects.filter(expense_date__range=[start_date.date(), end_date.date()])
	total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0
	expenses_by_category = expenses.values('category__name').annotate(total=Sum('amount')).order_by('-total')

	net_profit = total_sales - total_expenses
	sales_by_type = (
		SaleItem.objects.filter(sale__created_at__range=[start_date_aware, end_date_aware])
		.values('product__type')
		.annotate(total_revenue=Sum('total'), total_quantity=Sum('quantity'))
	)
	top_customers = (
		sales.values('customer__name')
		.annotate(total_spent=Sum('total'), purchase_count=Count('id'))
		.order_by('-total_spent')[:5]
	)

	return render(
		request,
		'reports/monthly_report.html',
		{
			'current_month': current_month,
			'current_year': current_year,
			'total_sales': total_sales,
			'sales_count': sales_count,
			'daily_sales': json.dumps(daily_sales),
			'total_expenses': total_expenses,
			'expenses_by_category': expenses_by_category,
			'net_profit': net_profit,
			'sales_by_type': sales_by_type,
			'top_customers': top_customers,
			'months': range(1, 13),
			'years': range(2020, now.year + 1),
		},
	)


@login_required
def sales_analytics(request):
	end_date = timezone.now()
	start_date = end_date - timedelta(days=365)

	monthly_agg = (
		Sale.objects.filter(created_at__range=[start_date, end_date])
		.annotate(month=TruncMonth('created_at'))
		.values('month')
		.annotate(total=Sum('total'))
		.order_by('month')
	)
	monthly_data = [{'month': item['month'].strftime('%Y-%m'), 'sales': float(item['total'] or 0)} for item in monthly_agg]
	total_sales = sum(item['sales'] for item in monthly_data)

	last_year_start = start_date - timedelta(days=365)
	last_year_sales = Sale.objects.filter(created_at__range=[last_year_start, start_date]).aggregate(total=Sum('total'))['total'] or 0
	growth_rate = ((total_sales - float(last_year_sales)) / float(last_year_sales) * 100) if last_year_sales else 0

	peak_seasons = (
		Sale.objects.annotate(month=TruncMonth('created_at'))
		.values('month')
		.annotate(total_sales=Sum('total'), total_count=Count('id'))
		.order_by('-total_sales')[:12]
	)

	return render(
		request,
		'reports/sales_analytics.html',
		{
			'monthly_data': json.dumps(monthly_data),
			'last_year_sales': last_year_sales,
			'growth_rate': growth_rate,
			'peak_seasons': peak_seasons,
		},
	)


@login_required
def profit_loss(request):
	now = timezone.now()
	start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

	revenue = Sale.objects.filter(created_at__gte=start_of_month).aggregate(total=Sum('total'))['total'] or 0
	cogs = (
		SaleItem.objects.filter(sale__created_at__gte=start_of_month)
		.annotate(cogs_line=ExpressionWrapper(F('quantity') * F('product__purchase_price'), output_field=DecimalField(max_digits=14, decimal_places=2)))
		.aggregate(total=Sum('cogs_line'))['total']
		or 0
	)

	gross_profit = revenue - cogs
	gross_margin = (gross_profit / revenue * 100) if revenue else 0
	operating_expenses = Expense.objects.filter(expense_date__gte=start_of_month.date()).aggregate(total=Sum('amount'))['total'] or 0
	net_profit = gross_profit - operating_expenses

	return render(
		request,
		'reports/profit_loss.html',
		{
			'revenue': revenue,
			'cogs': cogs,
			'gross_profit': gross_profit,
			'gross_margin': gross_margin,
			'operating_expenses': operating_expenses,
			'net_profit': net_profit,
		},
	)


@login_required
def smart_analysis(request):
	today = timezone.localdate()
	now = timezone.now()
	current_start = timezone.make_aware(datetime.combine(today - timedelta(days=29), datetime.min.time()))
	previous_start = current_start - timedelta(days=30)
	previous_end = current_start - timedelta(microseconds=1)

	current_sales = Sale.objects.filter(created_at__gte=current_start)
	previous_sales = Sale.objects.filter(created_at__range=[previous_start, previous_end])
	current_revenue = current_sales.aggregate(total=Sum('total'))['total'] or 0
	previous_revenue = previous_sales.aggregate(total=Sum('total'))['total'] or 0
	revenue_change = _percent_change(current_revenue, previous_revenue)

	current_expenses = Expense.objects.filter(expense_date__gte=current_start.date())
	previous_expenses = Expense.objects.filter(expense_date__range=[previous_start.date(), previous_end.date()])
	current_expense_total = current_expenses.aggregate(total=Sum('amount'))['total'] or 0
	previous_expense_total = previous_expenses.aggregate(total=Sum('amount'))['total'] or 0
	expense_change = _percent_change(current_expense_total, previous_expense_total)

	cogs = (
		SaleItem.objects.filter(sale__created_at__gte=current_start)
		.annotate(cogs_line=ExpressionWrapper(F('quantity') * F('product__purchase_price'), output_field=DecimalField(max_digits=14, decimal_places=2)))
		.aggregate(total=Sum('cogs_line'))['total']
		or 0
	)
	gross_profit = current_revenue - cogs
	net_profit = gross_profit - current_expense_total
	profit_margin = (net_profit / current_revenue * 100) if current_revenue else 0
	avg_invoice = current_revenue / current_sales.count() if current_sales.count() else 0

	top_products = (
		SaleItem.objects.filter(sale__created_at__gte=current_start)
		.values('product__name')
		.annotate(total_quantity=Sum('quantity'), total_revenue=Sum('total'))
		.order_by('-total_revenue')[:5]
	)
	top_expense = (
		current_expenses
		.values('category__name')
		.annotate(total=Sum('amount'))
		.order_by('-total')
		.first()
	)
	low_stock = Product.objects.filter(is_active=True, quantity__lte=F('min_stock')).order_by('quantity')[:6]
	slow_products = (
		Product.objects
		.filter(is_active=True)
		.exclude(saleitem__sale__created_at__gte=current_start)
		.order_by('-quantity')[:6]
	)

	insights = []
	if revenue_change > 10:
		insights.append({'level': 'success', 'title': 'المبيعات تتحسن', 'text': f'الإيرادات ارتفعت {revenue_change:.1f}% مقارنة بالفترة السابقة.'})
	elif revenue_change < -10:
		insights.append({'level': 'danger', 'title': 'انخفاض في المبيعات', 'text': f'الإيرادات انخفضت {abs(revenue_change):.1f}%، راجع المنتجات الأكثر طلبًا والعروض.'})
	else:
		insights.append({'level': 'info', 'title': 'المبيعات مستقرة', 'text': 'الإيرادات قريبة من الفترة السابقة، ويمكن تحسينها بعرض محدود على المنتجات الراكدة.'})

	if expense_change > 15:
		insights.append({'level': 'warning', 'title': 'المصروفات مرتفعة', 'text': f'المصروفات زادت {expense_change:.1f}%، راقب أكبر بند مصروفات خلال هذه الفترة.'})
	if profit_margin < 15 and current_revenue:
		insights.append({'level': 'warning', 'title': 'هامش الربح يحتاج انتباه', 'text': f'هامش صافي الربح {profit_margin:.1f}%، قد تحتاج لمراجعة التسعير أو تكلفة الشراء.'})
	if low_stock:
		insights.append({'level': 'danger', 'title': 'تنبيه مخزون', 'text': f'يوجد {Product.objects.filter(is_active=True, quantity__lte=F("min_stock")).count()} منتج عند الحد الأدنى أو أقل.'})
	if not current_sales.exists():
		insights.append({'level': 'info', 'title': 'لا توجد مبيعات حديثة', 'text': 'ابدأ بإضافة مبيعات من نقطة البيع حتى تظهر تحليلات أدق.'})

	return render(
		request,
		'reports/smart_analysis.html',
		{
			'current_revenue': current_revenue,
			'previous_revenue': previous_revenue,
			'revenue_change': revenue_change,
			'revenue_trend': _trend_label(revenue_change),
			'current_expense_total': current_expense_total,
			'expense_change': expense_change,
			'net_profit': net_profit,
			'gross_profit': gross_profit,
			'profit_margin': profit_margin,
			'avg_invoice': avg_invoice,
			'top_products': top_products,
			'top_expense': top_expense,
			'low_stock': low_stock,
			'slow_products': slow_products,
			'insights': insights,
			'period_start': current_start.date(),
			'period_end': today,
		},
	)
