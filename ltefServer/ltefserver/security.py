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