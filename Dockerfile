# Production Dockerfile for Django Mall Server
# Based on verified dev environment configuration
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
ENV DJANGO_SETTINGS_MODULE=mall_server.settings
ENV ENVIRONMENT=production

# Set timezone to Shanghai
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Set work directory
WORKDIR /app

# Install system dependencies using Tsinghua mirrors
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        default-libmysqlclient-dev \
        pkg-config \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies using Tsinghua PyPI mirror
COPY requirements.txt /app/
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple \
    && pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn

# Copy project files
COPY . /app/

# Create necessary directories
RUN mkdir -p /app/media /app/logs /app/static

# Collect static files (for production)
RUN python manage.py collectstatic --noinput || true

# Expose port 80 for production
EXPOSE 80

# Use gunicorn for production deployment
# 4 workers with auto-reload and proper logging
CMD ["gunicorn", "mall_server.wsgi:application", \
     "--bind", "0.0.0.0:80", \
     "--workers", "4", \
     "--worker-class", "sync", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info"]
