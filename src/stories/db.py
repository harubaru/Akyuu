from typing import Optional
import src.db.crud.user as user
from src.db.schemas.user import User, Story
from src.db.database import async_session

async def user_create(id: int, gensettings: str, storyids: str, quota: int) -> Optional[User]:
    async with async_session() as session, session.begin():
        return await user.user.create_user(
            session=session,
            id=id,
            gensettings=gensettings,
            storyids=storyids,
            quota=quota
        )

async def user_update(id: int, gensettings: str, storyids: str, quota: int) -> Optional[User]:
    async with async_session() as session, session.begin():
        return await user.user.update_user(
            session=session,
            id=id,
            gensettings=gensettings,
            storyids=storyids,
            quota=quota
        )

async def user_delete(id: int) -> Optional[User]:
    async with async_session() as session, session.begin():
        return await user.user.delete_user(
            session=session,
            id=id
        )

async def user_get(id: int) -> Optional[User]:
    async with async_session() as session, session.begin():
        return await user.user.get_by_ids(
            session=session,
            id=id
        )

async def story_create(uuid: str, owner_id: int, content_metadata: str, content: str) -> Optional[Story]:
    async with async_session() as session, session.begin():
        return await user.story.create_story(
            session=session,
            uuid=uuid,
            owner_id=owner_id,
            content_metadata=content_metadata,
            content=content
        )

async def story_update(uuid: str, content_metadata: str, content: str) -> Optional[Story]:
    async with async_session() as session, session.begin():
        return await user.story.update_story(
            session=session,
            uuid=uuid,
            content_metadata=content_metadata,
            content=content
        )

async def story_delete(uuid: str) -> Optional[Story]:
    async with async_session() as session, session.begin():
        return await user.story.delete_story(
            session=session,
            uuid=uuid
        )

async def story_get(uuid: str) -> Optional[Story]:
    async with async_session() as session, session.begin():
        return await user.story.get_by_ids(
            session=session,
            uuid=uuid
        )
