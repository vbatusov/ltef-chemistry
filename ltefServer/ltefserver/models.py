from sqlalchemy import (
    Column,
    Index,
    Integer,
    Text,
    ForeignKey,
    )

from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import (
    scoped_session,
    sessionmaker,
    )

from zope.sqlalchemy import ZopeTransactionExtension

from pyramid.security import (
    Allow,
    Everyone,
    )

# Database

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()

class Group(Base):
    __tablename__ = 'groups'
    id = Column(Integer, primary_key=True)
    desc = Column(Text, unique=True)

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(Text, unique=True)
    group = Column(ForeignKey("groups.id"))
    phash = Column(Text)

# Store lists in a single table, intertwined?
# Or take the arms against the sea of troubles
# And by storing an array in each entry, end them?
class ListItems(Base):
    __tablename__ = 'lists'
    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True)
    owner = Column(ForeignKey("users.id"))
    desc = Column(Text)




# Authorization

class RootFactory(object):
    __acl__ = [ (Allow, 'admin', 'dominate'),
                (Allow, 'admin', 'educate'),
                (Allow, 'admin', 'study'),
                (Allow, 'teacher', 'educate'),
                (Allow, 'teacher', 'study'),
                (Allow, 'student', 'study'),
                (Allow, 'guest', 'study') ]
    def __init__(self, request):
        pass