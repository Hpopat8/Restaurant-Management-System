-- Run this in MySQL to set up / update your users table

CREATE DATABASE IF NOT EXISTS gtl_auth;
USE gtl_auth;

CREATE TABLE IF NOT EXISTS users (
    id        INT AUTO_INCREMENT PRIMARY KEY,
    user_id   VARCHAR(50)  UNIQUE NOT NULL,
    email     VARCHAR(100) UNIQUE NOT NULL,
    password  VARCHAR(255) NOT NULL DEFAULT '',
    google_id VARCHAR(100) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- If table already exists, just add the google_id column:
-- ALTER TABLE users ADD COLUMN google_id VARCHAR(100) DEFAULT NULL;
