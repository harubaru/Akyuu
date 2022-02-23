from src.db.base_class import Base
from sqlalchemy import Column, String, Table, BigInteger, Integer

class User(Base):
    __tablename__ = 'users'

    id = Column(BigInteger, primary_key=True, index=True)
    gensettings = Column(String, unique=False)
    storyids = Column(String, unique=False)
    quota = Column(Integer, unique=False)

class Story(Base):
    __tablename__ = 'stories'

    uuid = Column(String, primary_key=True, index=True, unique=True)
    owner_id = Column(BigInteger, index=True)
    content_metadata = Column(String, unique=False)
    content = Column(String, unique=False)
