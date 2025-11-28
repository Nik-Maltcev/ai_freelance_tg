"""Category service for managing freelance categories.

Provides methods for CRUD operations on Category model and syncing from config.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import Category


class CategoryService:
    """Service for managing categories."""

    def __init__(self, session: AsyncSession):
        """Initialize with database session.
        
        Args:
            session: Async SQLAlchemy session.
        """
        self.session = session

    async def get_all_active(self) -> list[Category]:
        """Get all active categories.
        
        Returns:
            List of active Category objects ordered by name.
        """
        result = await self.session.execute(
            select(Category)
            .where(Category.is_active == True)
            .order_by(Category.name)
        )
        return list(result.scalars().all())

    async def get_by_slug(self, slug: str) -> Category | None:
        """Get category by slug.
        
        Args:
            slug: Unique category identifier.
            
        Returns:
            Category object or None if not found.
        """
        result = await self.session.execute(
            select(Category).where(Category.slug == slug)
        )
        return result.scalar_one_or_none()


    async def sync_from_config(self, config: dict[str, Any]) -> None:
        """Sync categories from YAML config to database.
        
        Creates new categories, updates existing ones, and deactivates
        categories not in config.
        
        Args:
            config: Dictionary with "categories" key containing category objects.
                Each category should have "name" and "chats" fields.
        """
        categories_config = config.get("categories", {})
        config_slugs = set(categories_config.keys())
        
        # Get existing categories
        result = await self.session.execute(select(Category))
        existing_categories = {cat.slug: cat for cat in result.scalars().all()}
        existing_slugs = set(existing_categories.keys())
        
        # Create or update categories from config
        for slug, cat_data in categories_config.items():
            if slug in existing_categories:
                # Update existing category
                category = existing_categories[slug]
                category.name = cat_data.get("name", slug)
                category.description = cat_data.get("description")
                category.chats_count = len(cat_data.get("chats", []))
                category.is_active = True
            else:
                # Create new category
                category = Category(
                    slug=slug,
                    name=cat_data.get("name", slug),
                    description=cat_data.get("description"),
                    chats_count=len(cat_data.get("chats", [])),
                    is_active=True,
                )
                self.session.add(category)
        
        # Deactivate categories not in config
        slugs_to_deactivate = existing_slugs - config_slugs
        if slugs_to_deactivate:
            await self.session.execute(
                update(Category)
                .where(Category.slug.in_(slugs_to_deactivate))
                .values(is_active=False)
            )
        
        await self.session.commit()

    async def update_last_parsed(self, slug: str) -> None:
        """Update last_parsed_at timestamp for a category.
        
        Args:
            slug: Category slug to update.
        """
        await self.session.execute(
            update(Category)
            .where(Category.slug == slug)
            .values(last_parsed_at=datetime.utcnow())
        )
        await self.session.commit()
