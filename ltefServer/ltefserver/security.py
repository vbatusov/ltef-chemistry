from .models import (
    DBSession,
    Group,
    User,
    )

import bcrypt

def groupfinder(username, request):
    user = DBSession.query(User).filter_by(username=username).first()
    if user is not None:
        group = DBSession.query(Group).filter_by(id=user.group).first()
        if group is not None:
            return [group.desc]
    return None

def getHash(password):
    """ Assume password is in Unicode """
    return bcrypt.hashpw(password.encode('UTF-8'), bcrypt.gensalt())

def checkCredentials(username, password):
    ''' Apparently, DB returns Unicode strings, and the password parameter is Unicode.
        But bcrypt wants ASCII and nothing else.
    '''
    user = DBSession.query(User).filter_by(username=username).first()
    if user is not None:
        p = password.encode('UTF-8')
        h = user.phash.encode('UTF-8')

        if bcrypt.hashpw(p, h) == h:
            return True

    return False

def group_security(user):
    is_guest = Group.GUEST
    is_admin = None
    is_teacher = None
    is_student = None

    user = DBSession.query(User).filter_by(username=user).first()
    if user is not None:
        group = DBSession.query(Group).filter_by(id=user.group).first()
        if group is not None:
            is_admin = (group.desc == Group.ADMIN)
            is_teacher = (group.desc == Group.TEACHER)
            is_student = (group.desc == Group.STUDENT)
    return { "is_guest" : is_guest, "is_admin" : is_admin, "is_teacher" : is_teacher, "is_student" : is_student}
