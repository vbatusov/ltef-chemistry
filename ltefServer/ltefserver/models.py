from sqlalchemy import (
    Column,
    Index,
    Integer,
    Text,
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


class MyModel(Base):
    __tablename__ = 'models'
    id = Column(Integer, primary_key=True)
    name = Column(Text)
    value = Column(Integer)

Index('my_index', MyModel.name, unique=True, mysql_length=255)




# Authorization

class RootFactory(object):
    __acl__ = [ (Allow, 'group:guests', 'view'),
                # (Allow, Everyone, 'view'),
                (Allow, 'group:editors', 'view'),
                (Allow, 'group:editors', 'edit') ]
    def __init__(self, request):
        pass