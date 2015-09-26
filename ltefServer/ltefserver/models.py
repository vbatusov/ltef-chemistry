from sqlalchemy import (
    Column,
    Index,
    Integer,
    Text,
    ForeignKey,
    PickleType,
    DateTime,
    )

import datetime #<- will be used to set default dates on models
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

class Course(Base):
    __tablename__ = 'courses'

    id = Column(Integer, primary_key=True)  # Will be auto-filled
    name = Column(Text)        # Will need to be unique
    description = Column(Text)
    owner = Column(ForeignKey("users.id"))  # Link to another table's column
    access_code = Column(Text, unique=True)        # Again, needs to be unique

    @classmethod
    def owner_courses(cls, owner):

        return DBSession.query(Course).filter(Course.owner == User.current_user(owner).id).all()

class Enrolled(Base):
    __tablename__ = 'enrollment'

    # Simply linking up two fields from different tables
    id = Column(Integer, primary_key=True)  # Will be auto-filled
    userid = Column(ForeignKey("users.id"))
    courseid = Column( ForeignKey("courses.id"))

    @classmethod
    def enrolled_courses(cls, username):
        return DBSession.query(Course).filter(Enrolled.courseid == Course.id).filter(Enrolled.userid == User.current_user(username).id).all()


class User(Base):
    __tablename__ = 'users'

    ADMIN = "admin"
    GUEST = "guest"

    id = Column(Integer, primary_key=True)
    firstname = Column(Text)
    lastname = Column(Text)
    studentNumber = Column(Integer)
    email = Column(Text, unique=True)
    username = Column(Text, unique=True)
    group = Column(ForeignKey("groups.id"))
    phash = Column(Text)

    @classmethod
    def current_user(cls, username):
        return DBSession.query(User).filter(User.username == username).first()



class Reac(Base):
    __tablename__ = 'reaction'

    id = Column(Integer, primary_key=True)
    basename = Column(Text, unique=True)
    source = Column(Text)
    source_timestamp = Column(DateTime)
    full_name = Column(Text)
    description = Column(Text)
    #obj = Column(PickleType)

class Customizable_reaction(Base):
    __tablename__ = 'customizable_reaction'

    id = Column(Integer, primary_key=True)
    reaction = Column(ForeignKey("reaction.id"))
    chapter = Column(ForeignKey("chapter.id"))
    title = Column(Text)
    description = Column(Text)
    setting = Column(PickleType)

class List(Base):
    __tablename__ = 'lists'

    ALL_TITLE = "All reactions"
    ALL_DESC = "All reactions currently stored in the database"

    id = Column(Integer, primary_key=True)
    owner = Column(ForeignKey("users.id"))
    title = Column(Text, unique=True)
    desc = Column(Text)
    data = Column(PickleType)

class Chapter(Base):
    __tablename__ = 'chapter'

    id = Column(Integer, primary_key=True)
    course = Column(ForeignKey("courses.id"))
    title = Column(Text)
    description = Column(Text)

class Quiz_history(Base):
    __tablename__ = 'quiz_history'

    id = Column(Integer, primary_key=True)
    course = Column(ForeignKey("courses.id"))
    chapter = Column(ForeignKey("chapter.id"))
    user = Column(ForeignKey("users.id"))
    question_number = Column(Integer)
    score = Column(Integer)
    quiz_type = Column(Text)
    reaction_name = Column(Text)
    time_submitted = Column(DateTime, default=datetime.datetime.utcnow)
    reaction_obj = Column(PickleType)
    choice_obj = Column(PickleType)

class Security_question(Base):
    __tablename__ = 'security_question'

    id = Column(Integer, primary_key=True)
    question = Column(Text)
    answer = Column(Text)
    user = Column(ForeignKey("users.id"))

class Generated_question(Base):
    __tablename__ = 'generated_question'

    id = Column(Integer, primary_key=True)
    user = Column(ForeignKey("users.id"))
    reaction = Column(ForeignKey("reaction.id"))
    chapter = Column(ForeignKey("chapter.id"))
    quiz_type = Column(Text)
    full_reaction = Column(PickleType)
    choices = Column(PickleType)

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
