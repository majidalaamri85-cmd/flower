from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'حذف كل البيانات ثم إعادة تعبئتها ببيانات تجريبية'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('⚠️ جاري حذف البيانات القديمة...'))
        call_command('flush', '--noinput')
        call_command('migrate')
        call_command('setup_permissions')
        call_command('seed_data')
        self.stdout.write(self.style.SUCCESS('✅ تم إعادة تعبئة قاعدة البيانات بنجاح!'))
