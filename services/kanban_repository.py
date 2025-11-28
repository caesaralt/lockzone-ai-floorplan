"""
Kanban Task Repository - Database operations for kanban tasks.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class KanbanRepository:
    """Repository for kanban task database operations."""
    
    def __init__(self, session: Session, organization_id: str):
        self.session = session
        self.organization_id = organization_id
    
    def list_tasks(self, archived: bool = False) -> List[Dict]:
        """List kanban tasks."""
        from database.models import KanbanTask
        
        query = self.session.query(KanbanTask).filter(
            KanbanTask.organization_id == self.organization_id,
            KanbanTask.archived == archived
        )
        
        if archived:
            query = query.order_by(KanbanTask.archived_at.desc())
        else:
            query = query.order_by(KanbanTask.created_at.desc())
        
        return [task.to_dict() for task in query.all()]
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """Get a single task by ID."""
        from database.models import KanbanTask
        
        task = self.session.query(KanbanTask).filter(
            KanbanTask.id == task_id,
            KanbanTask.organization_id == self.organization_id
        ).first()
        
        return task.to_dict() if task else None
    
    def create_task(self, data: Dict) -> Dict:
        """Create a new kanban task."""
        from database.models import KanbanTask
        
        position = data.get('position', {'x': 10, 'y': 10})
        
        task = KanbanTask(
            organization_id=self.organization_id,
            project_id=data.get('project_id'),
            job_id=data.get('job_id'),
            column=data.get('column', 'todo'),
            content=data.get('content', 'New Task'),
            notes=data.get('notes', ''),
            color=data.get('color', '#ffffff'),
            position_x=position.get('x', 10),
            position_y=position.get('y', 10),
            assigned_to=data.get('assigned_to'),
            pinned=data.get('pinned', False),
            due_date=self._parse_date(data.get('due_date')),
            priority=data.get('priority', 'normal'),
        )
        
        self.session.add(task)
        self.session.flush()
        return task.to_dict()
    
    def update_task(self, task_id: str, data: Dict) -> Optional[Dict]:
        """Update a kanban task."""
        from database.models import KanbanTask
        
        task = self.session.query(KanbanTask).filter(
            KanbanTask.id == task_id,
            KanbanTask.organization_id == self.organization_id
        ).first()
        
        if not task:
            return None
        
        # Update fields
        if 'column' in data:
            task.column = data['column']
        if 'content' in data:
            task.content = data['content']
        if 'notes' in data:
            task.notes = data['notes']
        if 'color' in data:
            task.color = data['color']
        if 'position' in data:
            task.position_x = data['position'].get('x', task.position_x)
            task.position_y = data['position'].get('y', task.position_y)
        if 'due_date' in data:
            task.due_date = self._parse_date(data['due_date'])
        if 'assigned_to' in data:
            task.assigned_to = data['assigned_to']
        if 'pinned' in data:
            task.pinned = data['pinned']
        if 'priority' in data:
            task.priority = data['priority']
        if 'archived' in data:
            task.archived = data['archived']
            if data['archived']:
                task.archived_at = datetime.utcnow()
            else:
                task.archived_at = None
        
        task.updated_at = datetime.utcnow()
        self.session.flush()
        return task.to_dict()
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a kanban task."""
        from database.models import KanbanTask
        
        task = self.session.query(KanbanTask).filter(
            KanbanTask.id == task_id,
            KanbanTask.organization_id == self.organization_id
        ).first()
        
        if not task:
            return False
        
        self.session.delete(task)
        return True
    
    def _parse_date(self, date_value):
        """Parse a date value."""
        if not date_value:
            return None
        if isinstance(date_value, str):
            try:
                from dateutil import parser
                return parser.parse(date_value).date()
            except:
                return None
        return date_value

