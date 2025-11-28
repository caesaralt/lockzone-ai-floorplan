"""
Inventory Repository - Database access layer for inventory/stock management.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import or_

from database.models import InventoryItem

logger = logging.getLogger(__name__)


class InventoryRepository:
    """Repository for inventory database operations."""
    
    def __init__(self, session: Session, organization_id: str):
        self.session = session
        self.organization_id = organization_id
    
    def list_items(self, category: str = None, active_only: bool = True,
                   low_stock_only: bool = False) -> List[Dict]:
        """List inventory items with optional filters."""
        query = self.session.query(InventoryItem).filter(
            InventoryItem.organization_id == self.organization_id
        )
        if active_only:
            query = query.filter(InventoryItem.is_active == True)
        if category:
            query = query.filter(InventoryItem.category == category)
        if low_stock_only:
            query = query.filter(InventoryItem.quantity <= InventoryItem.reorder_level)
        
        items = query.order_by(InventoryItem.name).all()
        return [item.to_dict() for item in items]
    
    def get_item(self, item_id: str) -> Optional[Dict]:
        """Get an inventory item by ID."""
        item = self.session.query(InventoryItem).filter(
            InventoryItem.id == item_id,
            InventoryItem.organization_id == self.organization_id
        ).first()
        return item.to_dict() if item else None
    
    def get_item_by_sku(self, sku: str) -> Optional[Dict]:
        """Get an inventory item by SKU."""
        item = self.session.query(InventoryItem).filter(
            InventoryItem.sku == sku,
            InventoryItem.organization_id == self.organization_id
        ).first()
        return item.to_dict() if item else None
    
    def create_item(self, data: Dict) -> Dict:
        """Create a new inventory item."""
        item = InventoryItem(
            organization_id=self.organization_id,
            supplier_id=data.get('supplier_id'),
            name=data.get('name', ''),
            sku=data.get('sku'),
            category=data.get('category'),
            description=data.get('description'),
            unit_price=data.get('unit_price', 0),
            cost_price=data.get('cost_price', 0),
            quantity=data.get('quantity', 0),
            reorder_level=data.get('reorder_level', 5),
            location=data.get('location'),
            serial_numbers=data.get('serial_numbers', []),
            image_url=data.get('image_url') or data.get('image'),
            extra_data=data.get('metadata', {})
        )
        self.session.add(item)
        self.session.flush()
        logger.info(f"Created inventory item: {item.id}")
        return item.to_dict()
    
    def update_item(self, item_id: str, data: Dict) -> Optional[Dict]:
        """Update an inventory item."""
        item = self.session.query(InventoryItem).filter(
            InventoryItem.id == item_id,
            InventoryItem.organization_id == self.organization_id
        ).first()
        if not item:
            return None
        
        for key in ['name', 'sku', 'category', 'description', 'unit_price',
                    'cost_price', 'quantity', 'reorder_level', 'location',
                    'serial_numbers', 'is_active']:
            if key in data:
                setattr(item, key, data[key])
        if 'metadata' in data:
            item.extra_data = data['metadata']
        
        if 'image_url' in data:
            item.image_url = data['image_url']
        elif 'image' in data:
            item.image_url = data['image']
        
        if 'supplier_id' in data:
            item.supplier_id = data['supplier_id'] or None
        
        item.updated_at = datetime.utcnow()
        self.session.flush()
        logger.info(f"Updated inventory item: {item_id}")
        return item.to_dict()
    
    def delete_item(self, item_id: str) -> bool:
        """Soft delete an inventory item."""
        item = self.session.query(InventoryItem).filter(
            InventoryItem.id == item_id,
            InventoryItem.organization_id == self.organization_id
        ).first()
        if not item:
            return False
        item.is_active = False
        item.updated_at = datetime.utcnow()
        self.session.flush()
        logger.info(f"Deleted (deactivated) inventory item: {item_id}")
        return True
    
    def adjust_quantity(self, item_id: str, adjustment: int, 
                       reason: str = None) -> Optional[Dict]:
        """Adjust inventory quantity (positive or negative)."""
        item = self.session.query(InventoryItem).filter(
            InventoryItem.id == item_id,
            InventoryItem.organization_id == self.organization_id
        ).first()
        if not item:
            return None
        
        item.quantity = max(0, item.quantity + adjustment)
        item.updated_at = datetime.utcnow()
        self.session.flush()
        logger.info(f"Adjusted inventory {item_id} by {adjustment}: {reason}")
        return item.to_dict()
    
    def get_low_stock_items(self) -> List[Dict]:
        """Get all items that are at or below reorder level."""
        items = self.session.query(InventoryItem).filter(
            InventoryItem.organization_id == self.organization_id,
            InventoryItem.is_active == True,
            InventoryItem.quantity <= InventoryItem.reorder_level
        ).order_by(InventoryItem.quantity).all()
        return [item.to_dict() for item in items]
    
    def search_items(self, query: str) -> List[Dict]:
        """Search inventory items by name, SKU, or category."""
        search = f"%{query}%"
        items = self.session.query(InventoryItem).filter(
            InventoryItem.organization_id == self.organization_id,
            InventoryItem.is_active == True,
            or_(
                InventoryItem.name.ilike(search),
                InventoryItem.sku.ilike(search),
                InventoryItem.category.ilike(search)
            )
        ).all()
        return [item.to_dict() for item in items]
    
    def get_categories(self) -> List[str]:
        """Get list of unique categories."""
        result = self.session.query(InventoryItem.category).filter(
            InventoryItem.organization_id == self.organization_id,
            InventoryItem.is_active == True,
            InventoryItem.category.isnot(None)
        ).distinct().all()
        return [r[0] for r in result if r[0]]
    
    def get_stock_value(self) -> float:
        """Calculate total stock value."""
        items = self.session.query(InventoryItem).filter(
            InventoryItem.organization_id == self.organization_id,
            InventoryItem.is_active == True
        ).all()
        return sum(item.quantity * (item.cost_price or item.unit_price or 0) 
                   for item in items)

