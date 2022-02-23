from typing import Optional

from src.db.crud.base import CrudBase
from src.db.models.user import User, Story
from src.db.schemas.user import UserUpdate, StoryUpdate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

class CrudUser(CrudBase[User, User, UserUpdate]):
    async def get_by_ids(self, session: AsyncSession, id: int) -> Optional[User]:
        return (await session.execute(select(self.model).where(self.model.id == id))).scalars().first()
    
    async def create_user(self, session: AsyncSession, *, id: int, gensettings: str, storyids: str, quota: int) -> User:
        db_obj = User(
            id=id,
            gensettings=gensettings,
            storyids=storyids,
            quota=quota
        )

        session.add(db_obj)
        await session.commit()

        return db_obj
    
    async def update_user(self, session: AsyncSession, *, id: int, gensettings: str, storyids: str, quota: int) -> Optional[User]:
        db_obj = (await session.execute(select(self.model).where(self.model.id == id))).scalars().first()

        if db_obj is None:
            return None

        db_obj.gensettings = gensettings
        db_obj.storyids = storyids
        db_obj.quota = quota

        await session.commit()

        return db_obj
    
    async def delete_user(self, session: AsyncSession, id: int) -> Optional[User]:
        db_obj = (await session.execute(select(self.model).where(self.model.id == id))).scalars().first()

        if db_obj is None:
            return None

        await session.delete(db_obj)
        await session.commit()

        return db_obj

class StoryCrud(CrudBase[Story, Story, StoryUpdate]):
    async def get_by_ids(self, session: AsyncSession, uuid: str) -> Optional[Story]:
        return (await session.execute(select(self.model).where(self.model.uuid == uuid))).scalars().first()
    
    async def create_story(self, session: AsyncSession, *, uuid: str, owner_id: int, content_metadata: str, content: str) -> Story:
        db_obj = Story(
            uuid=uuid,
            owner_id=owner_id,
            content_metadata=content_metadata,
            content=content
        )

        session.add(db_obj)
        await session.commit()

        return db_obj
    
    async def update_story(self, session: AsyncSession, *, uuid: str, content_metadata: str, content: str) -> Optional[Story]:
        db_obj = (await session.execute(select(self.model).where(self.model.uuid == uuid))).scalars().first()

        if db_obj is None:
            return None

        db_obj.content_metadata = content_metadata
        db_obj.content = content

        await session.commit()

        return db_obj
    
    async def delete_story(self, session: AsyncSession, uuid: str) -> Optional[Story]:
        db_obj = (await session.execute(select(self.model).where(self.model.uuid == uuid))).scalars().first()

        if db_obj is None:
            return None

        await session.delete(db_obj)
        await session.commit()

        return db_obj

user = CrudUser(User)
story = StoryCrud(Story)