-- Run this in MySQL to set up / update your users table

CREATE DATABASE IF NOT EXISTS gtl_auth;
USE gtl_auth;

CREATE TABLE IF NOT EXISTS users (
    id        INT AUTO_INCREMENT PRIMARY KEY,
    user_id   VARCHAR(50)  UNIQUE NOT NULL,
    email     VARCHAR(100) UNIQUE NOT NULL,
    password  VARCHAR(255) NOT NULL DEFAULT '',
    phone     VARCHAR(20) DEFAULT NULL,
    google_id VARCHAR(100) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- If table already exists, just add the google_id column:
-- ALTER TABLE users ADD COLUMN google_id VARCHAR(100) DEFAULT NULL;

-- Table to store one-time passcodes (OTPs) for 2FA
CREATE TABLE IF NOT EXISTS otps (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    code VARCHAR(10) NOT NULL,
    channel ENUM('email','sms') NOT NULL,
    expires_at DATETIME NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX (user_id)
);
