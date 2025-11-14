# Dockerfile
FROM python:3.12-slim

# Set môi trường
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Cài các package hệ thống cần cho psycopg2, build…
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy file requirements và cài
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ project vào container
COPY . /app/

# Collect static nếu sau này có
# RUN python manage.py collectstatic --noinput

# Expose port cho gunicorn
EXPOSE 8000

# Lệnh chạy chính
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
