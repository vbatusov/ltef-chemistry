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
        DBSession.add(Group(desc='admin'))
        DBSession.add(Group(desc='teacher'))
        DBSession.add(Group(desc='student'))
        DBSession.add(Group(desc='guest'))

        print "Creating guest..."
        guestgroup = DBSession.query(Group).filter_by(desc='guest').first().id
        guesthash = bcrypt.hashpw('', bcrypt.gensalt())
        DBSession.add(User(username='guest', group=guestgroup, phash=guesthash))

        print "Creating superuser..."
        admingroup = DBSession.query(Group).filter_by(desc='admin').first().id
        adminpw = getpass.getpass()
        adminhash = bcrypt.hashpw(adminpw, bcrypt.gensalt())
        DBSession.add(User(username='admin', group=admingroup, phash=adminhash))
