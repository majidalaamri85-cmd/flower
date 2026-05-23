web: python manage.py migrate --noinput && python manage.py setup_permissions && python manage.py seed_expense_categories && python manage.py seed_data && gunicorn shop_management.wsgi:application --log-file -
worker: python manage.py process_tasks
