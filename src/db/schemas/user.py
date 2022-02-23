from pydantic import BaseModel

class User(BaseModel):
    id: int
    gensettings: str
    storyids: str
    quota: int

class Story(BaseModel):
    uuid: str
    owner_id: int
    content_metadata: str
    content: str

class UserUpdate(BaseModel):
    gensettings: str
    storyids: str
    quota: int

class StoryUpdate(BaseModel):
    content_metadata: str
    content: str