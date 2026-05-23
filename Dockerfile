FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

RUN mkdir -p /app/staticfiles /app/media /app/logs

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py setup_permissions && python manage.py seed_expense_categories && python manage.py seed_data && gunicorn shop_management.wsgi:application --bind 0.0.0.0:$PORT"]
