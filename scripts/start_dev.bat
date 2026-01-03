@echo off
REM Mall Server Development Environment Startup Script for Windows

echo === Mall Server Development Environment Setup ===

REM Check if .env.development exists
if not exist ".env.development" (
    echo Error: .env.development file not found!
    echo Please create .env.development file with required environment variables.
    pause
    exit /b 1
)

echo 1. Starting Docker services...
docker-compose -f docker-compose.dev.yml up -d mysql-mall redis-mall

echo 2. Waiting for services to be ready...
timeout /t 10 /nobreak > nul

echo 3. Installing Python dependencies...
pip install -r requirements.txt

echo 4. Setting up database...
python scripts/setup_dev_db.py

echo 5. Collecting static files...
python manage.py collectstatic --noinput --settings=mall_server.settings.development

echo 6. Starting Django development server...
python manage.py runserver 0.0.0.0:8001 --settings=mall_server.settings.development

echo === Development server started successfully! ===
echo Access the application at: http://localhost:8001
echo Admin interface: http://localhost:8001/admin/
echo API documentation: http://localhost:8001/api/docs/

pause