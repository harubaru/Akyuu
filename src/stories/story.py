from pydantic import BaseModel

import json
import uuid

from src.stories.db import (
    user_create, user_update, user_delete, user_get,
    story_create, story_update, story_delete, story_get
)
from src.stories.api import ModelProvider, ModelGenRequest
from src.stories.context import ContextEntry, ContextManager, Lorebook
from src.stories.context import (
    TRIM_DIR_BOTTOM, TRIM_DIR_NONE, TRIM_DIR_TOP,
    TRIM_TYPE_NEWLINE, TRIM_TYPE_SENTENCE, TRIM_TYPE_TOKEN,
    INSERTION_TYPE_NEWLINE, INSERTION_TYPE_SENTENCE, INSERTION_TYPE_TOKEN,
    tokenizer
)

STORY_TEXTTYPE_USER = 0
STORY_TEXTTYPE_AI = 1
STORY_TEXTTYPE_ALTERED = 2

class StoryMetadataV1(BaseModel):
    version: int = 1
    title: str = 'New Story'
    description: str = 'A new beginning...'
    memory: str = ''
    authorsNote: str = ''
    lorebook: str = None
    contextPreamble: bool = True

class StoryContentV1(BaseModel):
    version: int = 1
    entries: list = []

class Story:
    def __init__(self, story_uuid: str = None, owner_id: int=None, content_metadata: StoryMetadataV1=None, content: StoryContentV1=None):
        if story_uuid is None:
            story_uuid = str(uuid.uuid4())
        if owner_id is None:
            raise ValueError('owner_id is required')
        if content_metadata is None:
            content_metadata = StoryMetadataV1(
                title='New Story',
                memory='',
                authorsNote='',
                lorebook=None,
                contextPreamble=True
            )
        if content is None:
            content = StoryContentV1()
        
        self.story_uuid = story_uuid
        self.owner_id = owner_id
        self.content_metadata = content_metadata
        self.content = content

    def action(self, text, aitext=STORY_TEXTTYPE_USER):
        self.content.entries.append((text, aitext))
    
    def undo(self):
        if len(self.content.entries) > 0:
            self.content.entries.pop()
    
    async def save(self):
        if await story_get(self.story_uuid) is None:
            await story_create(self.story_uuid, self.owner_id, self.content_metadata.json(), self.content.json())
        else:
            await story_update(self.story_uuid, self.content_metadata.json(), self.content.json())
    
    async def load(self, story_uuid: str):
        story = await story_get(story_uuid)
        if story is None:
            raise ValueError('story not found')
        
        self.story_uuid = story_uuid
        self.owner_id = story.owner_id
        self.content_metadata = StoryMetadataV1(**json.loads(story.content_metadata))
        self.content = StoryContentV1(**json.loads(story.content))
    
    async def delete(self):
        await story_delete(self.story_uuid)

    def raw_txt(self, format=False, highlight_lastline=False, char_limit=256):
        story_str = ''

        for i, v in enumerate(self.content.entries):
            # check if v is the last entry
            if highlight_lastline:
                format = False
                if i == len(self.content.entries) - 1:
                    story_str += f'**{v[0]}**'
                    break
                else:
                    story_str += f'{v[0]}'
                continue
            if format:
                # bolden user text
                if v[1] == STORY_TEXTTYPE_USER:
                    story_str += f'**``{v[0]}``**'
                else:
                    story_str += f'``{v[0]}``'
            else:
                # raw text
                story_str += v[0]
        # trim to char limit if it is not None
        if char_limit is not None:
            if len(story_str) > char_limit:
                if format:
                    story_str = story_str[-char_limit:] + '...'
                else:
                    story_str = story_str[-char_limit:]

        return story_str
            
    def context(self, max_tokens=2048): # generate context based on content
        story_str = self.raw_txt()
        
        contextmgr = ContextManager(max_tokens)

        preamble = '***\n' if self.content_metadata.contextPreamble else ''
        if self.content_metadata.contextPreamble:
            max_tokens -= 1

        # Story Entry: Always included
        story_entry = ContextEntry(
            text=story_str,
            prefix='',
            suffix='',
            token_budget=2048,
            reserved_tokens=512,
            insertion_order=0,
            insertion_position=-1,
            trim_direction=TRIM_DIR_TOP,
            trim_type=TRIM_TYPE_SENTENCE,
            insertion_type=INSERTION_TYPE_NEWLINE,
            forced_activation=True,
            cascading_activation=True
        )

        memory_entry = ContextEntry(
            text=self.content_metadata.memory,
            prefix='',
            suffix='\n',
            token_budget=2048,
            reserved_tokens=0,
            insertion_order=800,
            insertion_position=0,
            trim_direction=TRIM_DIR_BOTTOM,
            trim_type=TRIM_TYPE_SENTENCE,
            insertion_type=INSERTION_TYPE_NEWLINE,
            forced_activation=True,
            cascading_activation=True
        )

        authorsnote_entry = ContextEntry(
            text=self.content_metadata.authorsNote,
            prefix='',
            suffix='\n',
            token_budget=2048,
            reserved_tokens=0,
            insertion_order=-400,
            insertion_position=-4,
            trim_direction=TRIM_DIR_BOTTOM,
            trim_type=TRIM_TYPE_SENTENCE,
            insertion_type=INSERTION_TYPE_NEWLINE,
            forced_activation=True,
            cascading_activation=True
        )

        lorebook = Lorebook('./lorebooks/touhou.lorebook')
        contextmgr.add_entries(lorebook.get_entries())
        contextmgr.add_entry(story_entry)
        contextmgr.add_entry(memory_entry)
        contextmgr.add_entry(authorsnote_entry)
        
        return preamble + contextmgr.context(max_tokens)
    
    def generate(self, provider: ModelProvider, request: ModelGenRequest, max_tokens=2048):
        request.prompt = self.context(max_tokens=max_tokens)
        aitext = provider.generate(request)
        self.action(aitext, STORY_TEXTTYPE_AI)

    def __repr__(self):
        return f'<Story {self.story_uuid}>'

    def __str__(self):
        return f'{self.story_uuid}'
