"""
Database seeding for LockZone AI Floorplan.
Creates default organization and admin user if database is empty.
"""

import logging
from werkzeug.security import generate_password_hash
from database.connection import get_db_session
from database.models import Organization, User

logger = logging.getLogger(__name__)

DEFAULT_ORG_NAME = "Integratd Living"
DEFAULT_ORG_SLUG = "integratd-living"
DEFAULT_ADMIN_EMAIL = "admin@integratdliving.com"
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"


def seed_default_organization(session):
    """Create default organization if none exists."""
    org = session.query(Organization).first()
    if org:
        logger.info(f"Organization already exists: {org.name}")
        return org
    
    org = Organization(
        name=DEFAULT_ORG_NAME,
        slug=DEFAULT_ORG_SLUG,
        settings={
            'timezone': 'Australia/Sydney',
            'currency': 'AUD',
            'default_markup': 20
        }
    )
    session.add(org)
    session.flush()
    logger.info(f"Created default organization: {org.name}")
    return org


def seed_default_admin(session, organization_id):
    """Create default admin user if none exists."""
    admin = session.query(User).filter_by(role='admin').first()
    if admin:
        logger.info(f"Admin user already exists: {admin.username}")
        return admin
    
    password_hash = generate_password_hash(DEFAULT_ADMIN_PASSWORD, method='pbkdf2:sha256')
    
    admin = User(
        organization_id=organization_id,
        email=DEFAULT_ADMIN_EMAIL,
        username=DEFAULT_ADMIN_USERNAME,
        password_hash=password_hash,
        display_name="Administrator",
        role='admin',
        permissions=['*'],
        is_active=True
    )
    session.add(admin)
    session.flush()
    logger.info(f"Created default admin user: {admin.username}")
    return admin


def seed_database():
    """
    Seed the database with default data if empty.
    Call this at application startup.
    """
    try:
        with get_db_session() as session:
            org = seed_default_organization(session)
            seed_default_admin(session, org.id)
            session.commit()
            logger.info("Database seeding completed successfully")
            return True
    except Exception as e:
        logger.error(f"Database seeding failed: {e}")
        raise


def get_default_organization_id():
    """Get the ID of the default organization."""
    try:
        with get_db_session() as session:
            org = session.query(Organization).filter_by(slug=DEFAULT_ORG_SLUG).first()
            if org:
                return org.id
            org = session.query(Organization).first()
            return org.id if org else None
    except Exception as e:
        logger.error(f"Failed to get default organization: {e}")
        return None


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    seed_database()

