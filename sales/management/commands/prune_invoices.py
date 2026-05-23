from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Sum

from sales.models import Customer, Sale


class Command(BaseCommand):
	help = 'Delete old invoices while keeping the most recent invoices.'

	def add_arguments(self, parser):
		parser.add_argument('--keep', type=int, default=5, help='Number of latest invoices to keep.')
		parser.add_argument('--yes', action='store_true', help='Actually delete invoices. Without this flag, only preview.')

	def handle(self, *args, **options):
		keep = options['keep']
		if keep < 0:
			raise CommandError('--keep must be zero or greater.')

		keep_ids = list(Sale.objects.order_by('-created_at', '-pk').values_list('pk', flat=True)[:keep])
		delete_qs = Sale.objects.exclude(pk__in=keep_ids)
		delete_count = delete_qs.count()
		total_count = Sale.objects.count()

		self.stdout.write(f'Total invoices: {total_count}')
		self.stdout.write(f'Invoices to keep: {len(keep_ids)}')
		self.stdout.write(f'Invoices to delete: {delete_count}')

		if not options['yes']:
			self.stdout.write(self.style.WARNING('Preview only. Re-run with --yes to delete.'))
			return

		with transaction.atomic():
			delete_qs.delete()
			for customer in Customer.objects.all():
				total = Sale.objects.filter(customer=customer).aggregate(total=Sum('total'))['total'] or 0
				last_purchase = Sale.objects.filter(customer=customer).order_by('-created_at').values_list('created_at', flat=True).first()
				customer.total_purchases = total
				customer.last_purchase_date = last_purchase
				customer.save(update_fields=['total_purchases', 'last_purchase_date'])

		self.stdout.write(self.style.SUCCESS(f'Deleted {delete_count} invoices. Kept {len(keep_ids)} latest invoices.'))
