from typing import List
from pydantic import BaseModel, ValidationError, validator

import json

from src.stories.api import ModelGenArgs, ModelLogitBiasArgs, ModelPhraseBiasArgs, ModelProvider, ModelSampleArgs, ModelGenRequest, ModelSerializer
from src.stories.db import (
    user_create, user_update, user_delete, user_get,
    story_create, story_update, story_delete, story_get
)
from src.stories.story import Story, STORY_TEXTTYPE_AI, STORY_TEXTTYPE_USER
from src.stories.utils import cut_trailing_sentence

class UserSettingsV1(BaseModel):
    version: int = 1
    settings: ModelGenRequest = None

    @validator('version')
    def validate_version(cls, v):
        if v != 1:
            raise ValidationError('version must be 1')
        return v

def default_settings():
    return ModelGenRequest(
        model='lit-6b',
        prompt='',
        gen_args=ModelGenArgs(
            max_length=40
        ),
        sample_args=ModelSampleArgs(
            temp=0.51,
            tfs=0.992,
            rep_p=1.125,
            rep_p_range=2048,
            bad_words=['[', ' [']
        )
    )

class User:
    def __init__(self, client_id: int = None, gensettings: ModelGenRequest = None, storyids: List = None, quota: int = None):
        if client_id is None:
            raise ValueError('client_id is required')
        if gensettings is None:
            gensettings = default_settings()
        if storyids is None:
            storyids = []
        if quota is None:
            quota = 2000

        self.client_id = client_id
        self.gensettings = gensettings
        self.storyids = storyids
        self.quota = quota

    async def save(self):
        if await user_get(self.client_id) is None:
            await user_create(self.client_id, json.dumps(self.gensettings, cls=ModelSerializer), json.dumps(self.storyids, cls=ModelSerializer), self.quota)
        else:
            await user_update(self.client_id, json.dumps(self.gensettings, cls=ModelSerializer), json.dumps(self.storyids, cls=ModelSerializer), self.quota)
    
    async def load(self, client_id: int):
        user = await user_get(client_id)
        if user is None:
            raise ValueError('user not found')

        self.client_id = client_id
        if type(json.loads(user.gensettings)) == str:
            user.gensettings = json.loads(user.gensettings)
        self.gensettings = ModelGenRequest(**json.loads(user.gensettings))
        self.storyids = json.loads(user.storyids)
        self.quota = user.quota
    
    async def delete(self):
        # delete stories
        for uuid in self.storyids:
            await story_delete(uuid)
        # delete user
        await user_delete(self.client_id)

    async def get_stories(self):
        stories = []
        for story_uuid in self.storyids:
            story = Story(story_uuid, id)
            await story.load(story_uuid)
            stories.append(story)
        return stories
    
    async def create_story(self):
        story = Story(None, self.client_id, None, None)
        self.storyids.append(story.story_uuid)
        await story.save()
        await self.save()
        return story
    
    async def delete_story(self, uuid: str):
        self.storyids.remove(uuid)
        await story_delete(uuid)
        await self.save()
    
    async def generate(self, context: str, newline_prefix: bool=True, uuid: str=None, provider: ModelProvider=None):
        if self.quota == 0:
            raise ValueError('quota exceeded')
        # todo handle quota

        story = Story(uuid, self.client_id)
        await story.load(uuid)
        if story is None:
            raise ValueError('story not found')
        
        if context is not None:
            prefix = '\n' if newline_prefix else ''
            context = context.rstrip()
            story.action(prefix+context, STORY_TEXTTYPE_USER)

        r = self.gensettings
        r.prompt = story.context(max_tokens=1280-r.gen_args.max_length)
        r.sample_args.bad_words = [' Author', 'Author', 'Chapter', ' Chapter', '***']
        aitext = cut_trailing_sentence(provider.generate(r))
        # check if aitext ends with a newline, if it doesn't, add one
        if aitext[-1] != '\n':
            aitext += '\n'
        story.action(aitext, STORY_TEXTTYPE_AI)
        await story.save()

        return story
    