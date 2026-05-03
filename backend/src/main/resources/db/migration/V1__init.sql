-- V1__init.sql
-- Core tables for Whistleblower and Ethics Hotline

CREATE TABLE reports (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
    status VARCHAR(50) NOT NULL DEFAULT 'SUBMITTED',
    is_anonymous BOOLEAN NOT NULL DEFAULT TRUE,
    reporter_name VARCHAR(255),
    reporter_email VARCHAR(255),
    department VARCHAR(100),
    incident_date DATE,
    location VARCHAR(255),
    ai_description TEXT,
    ai_recommendations TEXT,
    ai_report TEXT,
    ai_processed BOOLEAN DEFAULT FALSE,
    ai_fallback BOOLEAN DEFAULT FALSE,
    assigned_to VARCHAR(255),
    resolution_notes TEXT,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_reports_status ON reports(status);
CREATE INDEX idx_reports_category ON reports(category);
CREATE INDEX idx_reports_severity ON reports(severity);
CREATE INDEX idx_reports_created_at ON reports(created_at);
CREATE INDEX idx_reports_is_deleted ON reports(is_deleted);

CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'VIEWER',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);

INSERT INTO users (username, email, password_hash, role)
VALUES (
    'admin',
    'admin@company.com',
    '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBOsl7iAt6.zm',
    'ADMIN'
);