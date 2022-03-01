import json

from src.stories.db import (
    user_create, user_update, user_delete, user_get,
    story_create, story_update, story_delete, story_get
)
from src.stories.story import STORY_TEXTTYPE_ALTERED, STORY_TEXTTYPE_USER, StoryMetadataV1, StoryContentV1, Story
from src.stories.user import User
from src.stories.api import ModelProvider
from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)

# a dictionary that stores a user's current story uuid
current_stories = {}

# utils
def load_cache():
    global current_stories
    try:
        with open(settings.CURRENT_STORY_CACHE, 'r') as f:
            current_stories = json.load(f)
        # turn all keys into ints instead of strings
        current_stories = {int(k): v for k, v in current_stories.items()}
        logger.info('loaded cache')
    except FileNotFoundError:
        logger.info('cache not found, writing new cache')
        current_stories = {}

def save_cache():
    with open(settings.CURRENT_STORY_CACHE, 'w') as f:
        json.dump(current_stories, f)

async def get_user(id: int=None):
    if id is None:
        raise ValueError('id is required')
    if await user_get(id) is None:
        return None
    
    user = User(0)
    await user.load(id)
    return user

async def get_story(uuid: str=None):
    story = Story(uuid, id)
    await story.load(uuid)
    return story

async def get_current_story(id: int=None):
    if id not in current_stories:
        raise ValueError('A story must be selected using !selectstory')
    uuid = current_stories[id]
    story = await get_story(uuid)
    return story

# account commands

# !register
async def cmd_user_register(id: int=None):
    if id is None:
        raise ValueError('id is required')
    if await user_get(id) is not None:
        raise ValueError('user already exists')
    
    user = User(id)
    await user.save()
    return user

# !deleteaccount
async def cmd_user_delete(id: int=None):
    user = await get_user(id)
    if user is None:
        raise ValueError('user does not exist')
    await user.delete()

# !settings
async def cmd_user_settings(id: int=None):
    user = await get_user(id)
    if user is None:
        raise ValueError('user does not exist')
    return user.gensettings

# story commands

# !newstory
async def cmd_story_new(id: int=None, title: str=None, description: str=None, author: str=None, genre: str=None, tags: str=None, style: str=None):
    user = await get_user(id)
    if user is None:
        raise ValueError('user does not exist')
    story = await user.create_story()
    if title is not None:
        story.content_metadata.title = title
    if description is not None:
        story.content_metadata.description = description
    
    story.content_metadata.author = author
    story.content_metadata.genre = genre
    story.content_metadata.tags = tags
    story.content_metadata.style = style

    await story.save()
    return story.story_uuid

# !deletestory
async def cmd_story_delete(id: int=None):
    if id not in current_stories:
        raise ValueError('A story must be selected using !selectstory')
    uuid = current_stories[id]
    user = await get_user(id)
    await user.delete_story(uuid)

# !selectstory
async def cmd_story_select(id: int=None, uuid: str=None):
    user = await get_user(id)
    if uuid not in user.storyids:
        raise ValueError('story does not exist')
    current_stories[id] = uuid
    save_cache()
    story = await get_story(uuid)
    return story

# !liststory
async def cmd_story_list(id: int=None):
    user = await get_user(id)
    return await user.get_stories()

# !submit
async def cmd_story_submit(id: int=None, context: str=None, provider: ModelProvider=None, generate: bool=True):
    if id not in current_stories:
        raise ValueError('A story must be selected using !selectstory')
    uuid = current_stories[id]
    user = await get_user(id)
    story = await get_story(uuid)
    prefix = ''
    if len(story.content.entries) > 1:
        prefix = '\n' if story.content.entries[-1][0][-1] != '\n' else ''
        if context != None:
            context = prefix + context
    if generate:
        await user.generate(context, uuid, provider)
    else:
        if context[-1] != '\n':
            context += '\n'
        story.action(context, STORY_TEXTTYPE_USER)
        await story.save()

# !undo
async def cmd_story_undo(id: int=None):
    if id not in current_stories:
        raise ValueError('A story must be selected using !selectstory')
    uuid = current_stories[id]
    user = await get_user(id)
    if uuid not in user.storyids:
        raise ValueError('story does not exist')
    story = await get_story(uuid)
    story.undo()
    await story.save()

# !retry
async def cmd_story_retry(id: int=None, provider: ModelProvider=None):
    if id not in current_stories:
        raise ValueError('A story must be selected using !selectstory')
    uuid = current_stories[id]
    user = await get_user(id)
    if uuid not in user.storyids:
        raise ValueError('story does not exist')
    story = await get_story(uuid)
    story.undo()
    await story.save()
    await user.generate(None, uuid, provider)

# !alter
async def cmd_story_alter(id: int=None, new_text: str=None):
    if id not in current_stories:
        raise ValueError('A story must be selected using !selectstory')
    uuid = current_stories[id]
    user = await get_user(id)
    if uuid not in user.storyids:
        raise ValueError('story does not exist')
    story = await get_story(uuid)
    story.undo()
    story.action('\n'+new_text, STORY_TEXTTYPE_ALTERED)
    await story.save()

# !memory
async def cmd_story_memory(id: int=None, memory: str=None):
    if id not in current_stories:
        raise ValueError('A story must be selected using !selectstory')
    uuid = current_stories[id]
    user = await get_user(id)
    if uuid not in user.storyids:
        raise ValueError('story does not exist')
    story = await get_story(uuid)
    if memory is not None:
        story.content_metadata.memory = memory
    await story.save()

# !authorsnote
async def cmd_story_authorsnote(id: int=None, note: str=None):
    if id not in current_stories:
        raise ValueError('A story must be selected using !selectstory')
    uuid = current_stories[id]
    user = await get_user(id)
    if uuid not in user.storyids:
        raise ValueError('story does not exist')
    story = await get_story(uuid)
    if note is not None:
        story.content_metadata.authorsNote = f'[ A/N: {note} ]'
    await story.save()

# !add
async def cmd_story_add(id: int=None, added_text: str=None):
    if id not in current_stories:
        raise ValueError('A story must be selected using !selectstory')
    uuid = current_stories[id]
    user = await get_user(id)
    if uuid not in user.storyids:
        raise ValueError('story does not exist')
    story = await get_story(uuid)
    story.undo()
    # add a newline if the last character isn't a newline
    prefix = '\n' if story.content.entries[-1][0][-1] != '\n' else ''
    story.action(f'{prefix+added_text}\n', STORY_TEXTTYPE_USER)
    await story.save()

# !edit
async def cmd_story_edit(id: int=None, new_title: str=None, new_description: str=None, new_author: str=None, new_genre: str=None, new_tags: str=None, new_style: str=None):
    if id not in current_stories:
        raise ValueError('A story must be selected using !selectstory')
    uuid = current_stories[id]
    user = await get_user(id)
    if uuid not in user.storyids:
        raise ValueError('story does not exist')
    story = await get_story(uuid)
    story.undo()
    if new_title is not None:
        story.content_metadata.title = new_title
    if new_description is not None:
        story.content_metadata.description = new_description
    if new_author is not None:
        story.content_metadata.author = new_author
    if new_genre is not None:
        story.content_metadata.genre = new_genre
    if new_tags is not None:
        story.content_metadata.tags = new_tags
    if new_style is not None:
        story.content_metadata.style = new_style
    await story.save()
