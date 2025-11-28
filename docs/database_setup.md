# Database Setup Guide

This document explains how to set up and configure the PostgreSQL database for the LockZone AI Floorplan application.

## Overview

The application uses PostgreSQL as its primary data store for all CRM and operational data. When `DATABASE_URL` is configured, the app automatically switches from JSON file storage to PostgreSQL.

## Environment Variables

### Required

```bash
DATABASE_URL=postgresql://user:password@host:port/database
```

**Format:** `postgresql://username:password@hostname:port/database_name`

**Example (Render):**
```bash
DATABASE_URL=postgresql://lockzone_user:secret123@dpg-xyz123.render.com:5432/lockzone_db
```

### Optional

```bash
ANTHROPIC_API_KEY=sk-ant-xxx  # For AI features
```

## Local Development Setup

### 1. Install PostgreSQL

**macOS (Homebrew):**
```bash
brew install postgresql@15
brew services start postgresql@15
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

### 2. Create Database

```bash
# Connect to PostgreSQL
psql postgres

# Create database and user
CREATE DATABASE lockzone_dev;
CREATE USER lockzone_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE lockzone_dev TO lockzone_user;
\q
```

### 3. Set Environment Variable

```bash
export DATABASE_URL=postgresql://lockzone_user:your_password@localhost:5432/lockzone_dev
```

Or create a `.env` file:
```
DATABASE_URL=postgresql://lockzone_user:your_password@localhost:5432/lockzone_dev
```

### 4. Run Migrations

```bash
# Install dependencies
pip install alembic psycopg2-binary

# Run migrations to create tables
alembic upgrade head
```

### 5. Start the Application

```bash
python app.py
```

You should see:
```
✅ Using PostgreSQL storage for CRM/operations data (DATABASE_URL detected)
✅ CRM Database Layer initialized successfully
```

## Production Setup (Render)

### 1. Create PostgreSQL Database on Render

1. Go to your Render dashboard
2. Click "New" → "PostgreSQL"
3. Choose a name and region
4. Select your plan (Starter is fine for testing)
5. Click "Create Database"

### 2. Get Connection String

1. Go to your database dashboard
2. Copy the "External Database URL"
3. It looks like: `postgres://user:pass@host:5432/dbname`

### 3. Add to Web Service

1. Go to your web service on Render
2. Click "Environment"
3. Add: `DATABASE_URL` = (paste your connection string)
4. Click "Save Changes"

### 4. Deploy

The app will automatically:
1. Detect `DATABASE_URL`
2. Run migrations on startup (via Alembic)
3. Seed default organization and admin user
4. Start using PostgreSQL for all CRM data

## Running Migrations

### Create a New Migration

```bash
# Auto-generate from model changes
alembic revision --autogenerate -m "Description of changes"

# Or create empty migration
alembic revision -m "Description of changes"
```

### Apply Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Apply one migration at a time
alembic upgrade +1

# Rollback one migration
alembic downgrade -1

# Rollback all migrations
alembic downgrade base
```

### View Migration Status

```bash
alembic current  # Show current revision
alembic history  # Show all revisions
```

## Database Schema

### Core Tables

| Table | Description |
|-------|-------------|
| `organizations` | Multi-tenant foundation |
| `users` | User accounts and authentication |
| `customers` | Customer/client records |
| `projects` | Projects linked to customers |
| `jobs` | Work orders within projects |
| `technicians` | Field workers |
| `suppliers` | Vendors/suppliers |
| `inventory_items` | Stock/inventory |
| `price_classes` | Quote automation price groups |
| `quotes` | Estimates and quotes |
| `communications` | Notes, emails, calls |
| `calendar_events` | Scheduling |
| `documents` | File attachments |

### AI Tables

| Table | Description |
|-------|-------------|
| `event_log` | Activity tracking for AI context |
| `document_index` | Document embeddings for RAG |

## Troubleshooting

### "DATABASE_URL not configured"

Make sure the environment variable is set:
```bash
echo $DATABASE_URL
```

### "Cannot connect to database"

1. Check the connection string format
2. Verify the database server is running
3. Check firewall/network settings
4. Verify credentials

### "Relation does not exist"

Migrations haven't been run:
```bash
alembic upgrade head
```

### Switching Back to JSON

If you need to temporarily use JSON storage:
```bash
unset DATABASE_URL
python app.py
```

## Data Migration (JSON → PostgreSQL)

If you have existing data in JSON files that you want to migrate:

```python
# Run this script once after setting up the database
python scripts/migrate_json_to_db.py
```

Note: This is optional. The app can start fresh with an empty database.

## Backup and Restore

### Backup

```bash
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
```

### Restore

```bash
psql $DATABASE_URL < backup_20231128.sql
```

## Performance Tips

1. **Indexes**: The schema includes indexes on frequently queried columns
2. **Connection Pooling**: The app uses SQLAlchemy's connection pool (5 connections, 10 overflow)
3. **Query Optimization**: Use the repository layer methods which are optimized for common operations

## Security

1. Never commit `DATABASE_URL` to version control
2. Use strong passwords in production
3. Enable SSL for production connections (Render does this automatically)
4. Regularly rotate database credentials

