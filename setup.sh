#!/usr/bin/env bash
set -o errexit

python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py setup_permissions || true
python manage.py seed_expense_categories || true
