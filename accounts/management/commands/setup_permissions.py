from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'إعداد الصلاحيات والمجموعات للموظفين'

    def handle(self, *args, **kwargs):
        groups = {
            'admin': 'مدير النظام - كامل الصلاحيات',
            'manager': 'مدير المحل - صلاحيات الإدارة بدون تغيير الإعدادات',
            'cashier': 'كاشير - البيع وعرض الفواتير فقط',
            'inventory_clerk': 'موظف مخزون - إدارة المنتجات والموردين',
            'accountant': 'محاسب - المصروفات والتقارير',
        }

        for group_name in groups:
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'تم إنشاء مجموعة: {group_name}'))

        permission_map = {
            'cashier': [
                ('add_sale', 'sales', 'sale'),
                ('view_sale', 'sales', 'sale'),
                ('view_customer', 'sales', 'customer'),
                ('add_customer', 'sales', 'customer'),
                ('view_product', 'inventory', 'product'),
            ],
            'inventory_clerk': [
                ('add_product', 'inventory', 'product'),
                ('change_product', 'inventory', 'product'),
                ('delete_product', 'inventory', 'product'),
                ('view_product', 'inventory', 'product'),
                ('add_supplier', 'inventory', 'supplier'),
                ('change_supplier', 'inventory', 'supplier'),
                ('view_supplier', 'inventory', 'supplier'),
                ('add_stockmovement', 'inventory', 'stockmovement'),
                ('view_stockmovement', 'inventory', 'stockmovement'),
            ],
            'accountant': [
                ('add_expense', 'accounts', 'expense'),
                ('change_expense', 'accounts', 'expense'),
                ('view_expense', 'accounts', 'expense'),
                ('view_sale', 'sales', 'sale'),
                ('view_stockmovement', 'inventory', 'stockmovement'),
            ],
        }

        for group_name, perms in permission_map.items():
            group = Group.objects.get(name=group_name)
            for codename, app_label, model in perms:
                try:
                    content_type = ContentType.objects.get(app_label=app_label, model=model)
                    permission = Permission.objects.get(codename=codename, content_type=content_type)
                    group.permissions.add(permission)
                except (ContentType.DoesNotExist, Permission.DoesNotExist):
                    continue

        self.stdout.write(self.style.SUCCESS('تم إعداد الصلاحيات بنجاح'))
