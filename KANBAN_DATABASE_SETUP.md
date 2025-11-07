# Kanban Board - Persistent Database Setup

This guide explains how to set up persistent storage for your Kanban board on Render using PostgreSQL.

## Why Database Storage?

Currently, the kanban board saves tasks to a JSON file which gets wiped every time you deploy to Render. With PostgreSQL database storage, your tasks will persist across all deployments and updates.

## Setup Instructions for Render

### Step 1: Create a PostgreSQL Database on Render

1. Go to your [Render Dashboard](https://dashboard.render.com/)
2. Click **"New +"** → **"PostgreSQL"**
3. Configure your database:
   - **Name**: `lockzone-kanban-db` (or any name you prefer)
   - **Database**: `kanban` (or any name)
   - **User**: (auto-generated)
   - **Region**: Same as your web service for best performance
   - **Plan**: Free tier is sufficient for now
4. Click **"Create Database"**
5. Wait for the database to be provisioned (takes ~2 minutes)

### Step 2: Get Your Database URL

1. Once created, click on your database
2. Scroll down to the **"Connections"** section
3. Copy the **"Internal Database URL"** (starts with `postgres://`)
   - Use the Internal URL since your app is also on Render
   - Format: `postgres://user:password@host/database`

### Step 3: Add Database URL to Your Web Service

1. Go to your web service on Render dashboard
2. Click **"Environment"** in the left sidebar
3. Click **"Add Environment Variable"**
4. Add:
   - **Key**: `DATABASE_URL`
   - **Value**: Paste the Internal Database URL from Step 2
5. Click **"Save Changes"**

### Step 4: Deploy Your Updated Code

1. Commit and push your code changes:
   ```bash
   git add .
   git commit -m "Add PostgreSQL database support for Kanban board"
   git push origin main
   ```

2. Render will automatically deploy the new version

3. The database tables will be created automatically on first run

### Step 5: Migrate Existing Tasks (Optional)

If you have existing tasks in the JSON file that you want to migrate:

1. On Render, go to your web service → **"Shell"**
2. Run the migration script:
   ```bash
   python migrate_kanban_to_db.py
   ```
3. Follow the prompts to migrate your data

**OR** run locally before deploying:

```bash
# Set your database URL locally
export DATABASE_URL="your-postgres-url-here"

# Run migration
python migrate_kanban_to_db.py
```

## How It Works

- **With DATABASE_URL set**: App uses PostgreSQL (persistent across deployments)
- **Without DATABASE_URL**: App uses JSON file (gets wiped on deploy)

The app automatically detects which storage method to use based on the `DATABASE_URL` environment variable.

## Database Schema

The `kanban_tasks` table includes:

| Column | Type | Description |
|--------|------|-------------|
| id | String(36) | Unique task ID (UUID) |
| column | String(50) | Column name (todo, working, etc.) |
| content | Text | Task content/description |
| notes | Text | Additional notes |
| color | String(7) | Task card color (hex) |
| position_x | Float | Horizontal position in column |
| position_y | Float | Vertical position in column |
| assigned_to | String(100) | Person assigned to task |
| pinned | Boolean | Whether task is pinned |
| due_date | String(20) | Due date (YYYY-MM-DD) |
| created_at | DateTime | When task was created |
| updated_at | DateTime | When task was last updated |

## Verification

After setup, you can verify the database is working:

1. Create a new task in your Kanban board
2. Redeploy your app on Render
3. Check if the task is still there after deployment
4. ✅ If yes, database is working correctly!

## Troubleshooting

**Tasks still disappearing after deploy:**
- Check that `DATABASE_URL` environment variable is set correctly
- Check Render logs for "Database tables created successfully" message
- Verify the database URL format is correct

**"No module named 'psycopg2'" error:**
- Make sure `psycopg2-binary==2.9.9` is in `requirements.txt`
- Redeploy to install the new dependency

**Database connection errors:**
- Verify database is running on Render dashboard
- Use Internal Database URL (not External) if app is on Render
- Check database and web service are in the same region

## Cost

- PostgreSQL Free tier on Render:
  - Storage: 1 GB
  - RAM: 256 MB
  - Connections: 97
  - Perfect for a kanban board!

## Backup

To backup your tasks:

```bash
# On Render Shell or locally with DATABASE_URL set
python -c "from app import app, db, KanbanTask; \
           import json; \
           with app.app_context(): \
               tasks = [t.to_dict() for t in KanbanTask.query.all()]; \
               print(json.dumps(tasks, indent=2))" > backup.json
```

## Support

If you encounter any issues, check:
1. Render deployment logs
2. Database connection details
3. Environment variables are set correctly
