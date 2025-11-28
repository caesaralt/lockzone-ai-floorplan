"""
Users Repository - Database access layer for user management.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from werkzeug.security import generate_password_hash, check_password_hash

from database.models import User

logger = logging.getLogger(__name__)


class UsersRepository:
    """Repository for user database operations."""
    
    def __init__(self, session: Session, organization_id: str = None):
        self.session = session
        self.organization_id = organization_id
    
    def list_users(self, active_only: bool = True) -> List[Dict]:
        """List all users."""
        query = self.session.query(User)
        if self.organization_id:
            query = query.filter(User.organization_id == self.organization_id)
        if active_only:
            query = query.filter(User.is_active == True)
        users = query.order_by(User.username).all()
        return [u.to_dict() for u in users]
    
    def get_user(self, user_id: str) -> Optional[Dict]:
        """Get a user by ID."""
        user = self.session.query(User).filter(User.id == user_id).first()
        return user.to_dict() if user else None
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get a user by username (returns model for auth)."""
        return self.session.query(User).filter(User.username == username).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email (returns model for auth)."""
        return self.session.query(User).filter(User.email == email).first()
    
    def create_user(self, data: Dict) -> Dict:
        """Create a new user."""
        password = data.get('password', 'changeme')
        password_hash = generate_password_hash(password, method='pbkdf2:sha256')
        
        user = User(
            organization_id=data.get('organization_id') or self.organization_id,
            email=data.get('email', ''),
            username=data.get('username', ''),
            password_hash=password_hash,
            display_name=data.get('display_name'),
            role=data.get('role', 'user'),
            permissions=data.get('permissions', []),
            is_active=data.get('is_active', True)
        )
        self.session.add(user)
        self.session.flush()
        logger.info(f"Created user: {user.id}")
        return user.to_dict()
    
    def update_user(self, user_id: str, data: Dict) -> Optional[Dict]:
        """Update a user."""
        user = self.session.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        for key in ['email', 'username', 'display_name', 'role', 
                    'permissions', 'is_active']:
            if key in data:
                setattr(user, key, data[key])
        
        if 'password' in data and data['password']:
            user.password_hash = generate_password_hash(
                data['password'], method='pbkdf2:sha256'
            )
        
        user.updated_at = datetime.utcnow()
        self.session.flush()
        logger.info(f"Updated user: {user_id}")
        return user.to_dict()
    
    def delete_user(self, user_id: str) -> bool:
        """Soft delete a user."""
        user = self.session.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        user.is_active = False
        user.updated_at = datetime.utcnow()
        self.session.flush()
        logger.info(f"Deleted (deactivated) user: {user_id}")
        return True
    
    def verify_password(self, user: User, password: str) -> bool:
        """Verify a user's password."""
        return check_password_hash(user.password_hash, password)
    
    def update_last_login(self, user_id: str) -> None:
        """Update user's last login timestamp."""
        user = self.session.query(User).filter(User.id == user_id).first()
        if user:
            user.last_login = datetime.utcnow()
            self.session.flush()
    
    def get_users_by_role(self, role: str) -> List[Dict]:
        """Get all users with a specific role."""
        query = self.session.query(User).filter(
            User.role == role,
            User.is_active == True
        )
        if self.organization_id:
            query = query.filter(User.organization_id == self.organization_id)
        users = query.all()
        return [u.to_dict() for u in users]

