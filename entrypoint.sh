#!/bin/bash
set -e

echo "=========================================="
echo "Starting Django Mall Server"
echo "=========================================="

# Run database migrations
echo ""
echo "Running database migrations..."
python manage.py migrate --noinput


echo "Loading from fixtures/initial_data.json..."
python manage.py loaddata fixtures/initial_data.json || echo "Warning: Failed to load fixtures, will use init_data.py instead"

# Collect static files (if needed)
echo ""
echo "Collecting static files..."
python manage.py collectstatic --noinput || echo "Warning: collectstatic failed, continuing..."

# Start server
echo ""
echo "=========================================="
echo "Starting Django server..."
echo "=========================================="
python manage.py runserver 0.0.0.0:80
