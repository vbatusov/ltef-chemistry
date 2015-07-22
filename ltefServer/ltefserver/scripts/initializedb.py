import os
import sys
import transaction
import getpass
import bcrypt

from sqlalchemy import engine_from_config

from pyramid.paster import (
    get_appsettings,
    setup_logging,
    )

from pyramid.scripts.common import parse_vars

from ..models import (
    
    DBSession,
    Group,
    User,
    Base,
    )


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri> [var=value]\n'
          '(example: "%s development.ini")' % (cmd, cmd))
    sys.exit(1)


def main(argv=sys.argv):
    if len(argv) < 2:
        usage(argv)
    config_uri = argv[1]
    options = parse_vars(argv[2:])
    setup_logging(config_uri)
    settings = get_appsettings(config_uri, options=options)
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.create_all(engine)
    with transaction.manager:
        print "Creating groups..."
        DBSession.add(Group(desc=Group.ADMIN))
        DBSession.add(Group(desc=Group.GUEST))
        DBSession.add(Group(desc=Group.TEACHER))
        DBSession.add(Group(desc=Group.STUDENT))

        print "Creating guest..."
        guestgroup = DBSession.query(Group).filter_by(desc=Group.GUEST).first().id
        guesthash = bcrypt.hashpw('', bcrypt.gensalt())
        DBSession.add(User(firstname=User.GUEST, lastname=User.GUEST, studentNumber="000000000",  username=User.GUEST, group=guestgroup, phash=guesthash))

        print "Creating superuser..."
        admingroup = DBSession.query(Group).filter_by(desc=Group.ADMIN).first().id
        adminpw = getpass.getpass()
        adminhash = bcrypt.hashpw(adminpw, bcrypt.gensalt())
        DBSession.add(User( firstname=User.ADMIN, lastname=User.ADMIN, studentNumber="000000000", username=User.ADMIN, group=admingroup, phash=adminhash))
