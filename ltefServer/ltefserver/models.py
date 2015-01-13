from sqlalchemy import (
    Column,
    Index,
    Integer,
    Text,
    ForeignKey,
    PickleType,
    DateTime,
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

    ADMIN = "admins"
    GUEST = "guests"
    TEACHER = "teachers"
    STUDENT = "students"

    id = Column(Integer, primary_key=True)
    desc = Column(Text, unique=True)

class User(Base):
    __tablename__ = 'users'

    ADMIN = "admin"
    GUEST = "guest"

    id = Column(Integer, primary_key=True)
    username = Column(Text, unique=True)
    group = Column(ForeignKey("groups.id"))
    phash = Column(Text)

class Reac(Base):
    __tablename__ = 'reactions'
    id = Column(Integer, primary_key=True)
    basename = Column(Text, unique=True)
    source = Column(Text)
    source_timestamp = Column(DateTime)
    full_name = Column(Text)
    description = Column(Text)
    #obj = Column(PickleType)

class List(Base):
    __tablename__ = 'lists'

    ALL_TITLE = "All reactions"
    ALL_DESC = "All reactions currently stored in the database"

    id = Column(Integer, primary_key=True)
    owner = Column(ForeignKey("users.id"))
    title = Column(Text, unique=True)
    desc = Column(Text)
    data = Column(PickleType)

# Authorization
class RootFactory(object):
    __acl__ = [ (Allow, Group.ADMIN, 'dominate'),
                (Allow, Group.ADMIN, 'educate'),
                (Allow, Group.ADMIN, 'study'),
                (Allow, Group.TEACHER, 'educate'),
                (Allow, Group.TEACHER, 'study'),
                (Allow, Group.STUDENT, 'study'),
                (Allow, Group.GUEST, 'study') ]
    def __init__(self, request):
        pass
