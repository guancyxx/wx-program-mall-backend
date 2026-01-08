#!/bin/bash
set -e

ls

# Start gunicorn
exec gunicorn mall_server.wsgi:application \
    --bind 0.0.0.0:80 \
    --workers 4 \
    --worker-class sync \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
