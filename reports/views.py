import json
from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import render
from django.utils import timezone

from accounts.models import Expense
from inventory.models import StockMovement
from sales.models import Sale, SaleItem


@login_required
def daily_report(request):
	today = timezone.localdate()
	selected_date = request.GET.get('date', today.isoformat())
	selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()

	start_of_day = timezone.make_aware(datetime.combine(selected_date, datetime.min.time()))
	end_of_day = timezone.make_aware(datetime.combine(selected_date, datetime.max.time()))

	sales = Sale.objects.filter(created_at__range=[start_of_day, end_of_day])
	total_sales = sales.aggregate(total=Sum('total'))['total'] or 0
	sales_count = sales.count()
	avg_sale = total_sales / sales_count if sales_count else 0

	payment_methods = sales.values('payment_method').annotate(total=Sum('total'), count=Count('id')).order_by('-total')
	expenses = Expense.objects.filter(created_at__range=[start_of_day, end_of_day])
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
	current_month = int(request.GET.get('month', now.month))
	current_year = int(request.GET.get('year', now.year))

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

	expenses = Expense.objects.filter(created_at__range=[start_date_aware, end_date_aware])
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
	operating_expenses = Expense.objects.filter(created_at__gte=start_of_month).aggregate(total=Sum('amount'))['total'] or 0
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
