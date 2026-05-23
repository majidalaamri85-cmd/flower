from django.core.management.base import BaseCommand

from accounts.models import ExpenseCategory


class Command(BaseCommand):
    help = 'إضافة فئات المصروفات الأساسية'

    def handle(self, *args, **kwargs):
        categories = [
            {'name': 'إيجار المحل', 'category_type': 'rent', 'icon': 'fas fa-building', 'color': 'primary'},
            {'name': 'رواتب الموظفين', 'category_type': 'salaries', 'icon': 'fas fa-users', 'color': 'success'},
            {'name': 'كهرباء وماء', 'category_type': 'utilities', 'icon': 'fas fa-bolt', 'color': 'warning'},
            {'name': 'شراء ورد طازج', 'category_type': 'supplies', 'icon': 'fas fa-leaf', 'color': 'danger'},
            {'name': 'شراء شوكولاته', 'category_type': 'supplies', 'icon': 'fas fa-candy-cane', 'color': 'info'},
            {'name': 'مواد تغليف', 'category_type': 'supplies', 'icon': 'fas fa-box', 'color': 'secondary'},
            {'name': 'توصيل طلبات', 'category_type': 'transport', 'icon': 'fas fa-truck', 'color': 'primary'},
            {'name': 'إعلانات وتسويق', 'category_type': 'marketing', 'icon': 'fas fa-ad', 'color': 'warning'},
            {'name': 'صيانة وتجديد', 'category_type': 'maintenance', 'icon': 'fas fa-tools', 'color': 'secondary'},
            {'name': 'أخرى', 'category_type': 'other', 'icon': 'fas fa-receipt', 'color': 'dark'},
        ]

        for cat_data in categories:
            category, created = ExpenseCategory.objects.get_or_create(name=cat_data['name'], defaults=cat_data)
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ تم إضافة: {category.name}'))
            else:
                self.stdout.write(f'• موجود مسبقا: {category.name}')

        self.stdout.write(self.style.SUCCESS('✅ تم إعداد فئات المصروفات بنجاح'))
