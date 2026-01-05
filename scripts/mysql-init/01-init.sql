-- Mall Server Development Database Initialization

-- Create database with proper charset
CREATE DATABASE IF NOT EXISTS mall_server_dev 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

-- Create user and grant privileges
CREATE USER IF NOT EXISTS 'mall_user'@'%' IDENTIFIED BY 'mall_password';
GRANT ALL PRIVILEGES ON mall_server_dev.* TO 'mall_user'@'%';

-- Grant privileges to root for development
GRANT ALL PRIVILEGES ON mall_server_dev.* TO 'root'@'%';

-- Flush privileges
FLUSH PRIVILEGES;

-- Use the database
USE mall_server_dev;

-- Create initial tables will be handled by Django migrations