#!/bin/bash
set -e

echo "=========================================="
echo "Starting Django Mall Server"
echo "=========================================="

# Run database migrations
echo ""
echo "Running database migrations..."
python manage.py migrate --noinput

# Create cache table if using DatabaseCache
echo ""
echo "Creating cache table(s)..."
python manage.py createcachetable --verbosity 0 || echo "Warning: createcachetable failed (table may already exist or not using DatabaseCache)"

# Load initial data
# echo ""
# echo "Loading from fixtures/initial_data.json..."
# python manage.py loaddata fixtures/initial_data.json || echo "Warning: Failed to load fixtures, will use init_data.py instead"

# Collect static files (if needed)
echo ""
echo "Collecting static files..."
python manage.py collectstatic --noinput || echo "Warning: collectstatic failed, continuing..."

# 更新 certifi
pip install --upgrade certifi

# 或者更新系统 CA 证书
apt-get update && apt-get install -y ca-certificates

# Start server
echo ""
echo "=========================================="
echo "Starting Django server..."
echo "=========================================="
python manage.py runserver 0.0.0.0:80
