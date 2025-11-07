#!/usr/bin/env python3
"""
Migration script to move kanban tasks from JSON file to PostgreSQL database
Run this once after setting up the database on Render
"""

import os
import json
from app import app, db, KanbanTask, USE_DATABASE, KANBAN_FILE

def migrate_json_to_database():
    """Migrate tasks from JSON file to database"""
    if not USE_DATABASE:
        print("❌ DATABASE_URL not set. Database is not configured.")
        print("Set the DATABASE_URL environment variable and try again.")
        return False

    if not os.path.exists(KANBAN_FILE):
        print(f"ℹ️  No existing JSON file found at {KANBAN_FILE}")
        print("Nothing to migrate.")
        return True

    # Read existing JSON data
    with open(KANBAN_FILE, 'r') as f:
        tasks_data = json.load(f)

    if not tasks_data:
        print("ℹ️  JSON file is empty. Nothing to migrate.")
        return True

    print(f"📋 Found {len(tasks_data)} tasks in JSON file")

    with app.app_context():
        # Create tables if they don't exist
        db.create_all()

        # Check if tasks already exist
        existing_count = KanbanTask.query.count()
        if existing_count > 0:
            response = input(f"⚠️  Database already contains {existing_count} tasks. Overwrite? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Migration cancelled")
                return False

            # Clear existing tasks
            KanbanTask.query.delete()
            db.session.commit()
            print(f"🗑️  Deleted {existing_count} existing tasks")

        # Migrate each task
        migrated = 0
        for task_data in tasks_data:
            try:
                position = task_data.get('position', {'x': 10, 'y': 10})

                task = KanbanTask(
                    id=task_data['id'],
                    column=task_data['column'],
                    content=task_data['content'],
                    notes=task_data.get('notes', ''),
                    color=task_data.get('color', '#ffffff'),
                    position_x=position.get('x', 10),
                    position_y=position.get('y', 10),
                    assigned_to=task_data.get('assigned_to'),
                    pinned=task_data.get('pinned', False),
                    due_date=task_data.get('due_date')
                )
                db.session.add(task)
                migrated += 1
            except Exception as e:
                print(f"❌ Error migrating task {task_data.get('id')}: {e}")

        db.session.commit()
        print(f"✅ Successfully migrated {migrated} tasks to database")

        # Verify migration
        final_count = KanbanTask.query.count()
        print(f"✅ Database now contains {final_count} tasks")

    return True

if __name__ == '__main__':
    print("🚀 Starting Kanban Data Migration")
    print("=" * 50)

    success = migrate_json_to_database()

    if success:
        print("\n" + "=" * 50)
        print("✅ Migration completed successfully!")
        print("\nYou can now:")
        print("1. Backup your JSON file: cp crm_data/kanban_tasks.json crm_data/kanban_tasks.json.backup")
        print("2. Deploy your app to Render")
        print("3. Your tasks will persist across deployments!")
    else:
        print("\n❌ Migration failed. Please check the errors above.")
