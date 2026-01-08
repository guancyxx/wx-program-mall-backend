#!/bin/bash
set -e

echo "=========================================="
echo "Starting Django Application Initialization"
echo "=========================================="

# Wait for database to be ready
echo "Waiting for database connection..."
python manage.py wait_for_db || {
    echo "Database connection failed, but continuing..."
}

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Load initial data from fixtures
echo "Loading initial data from fixtures..."
if [ -f "fixtures/initial_data.json" ]; then
    python manage.py loaddata fixtures/initial_data.json || echo "Initial data already loaded or load failed"
else
    echo "No initial_data.json found, skipping..."
fi

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear || echo "Static files collection skipped"

echo "=========================================="
echo "Initialization Complete"
echo "Starting Gunicorn Server on 0.0.0.0:80"
echo "=========================================="

# Start gunicorn
exec gunicorn mall_server.wsgi:application \
    --bind 0.0.0.0:80 \
    --workers 4 \
    --worker-class sync \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
