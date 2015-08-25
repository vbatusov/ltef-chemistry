from pyramid.view import (view_config, forbidden_view_config)
from pyramid.renderers import get_renderer
from pyramid.response import FileResponse, Response
from pyramid.request import Request
from pyramid.httpexceptions import (HTTPFound, HTTPNotFound)


from sqlalchemy.exc import DBAPIError
from ..models import (
    DBSession,
    Group,
    User,
    Reac,
    List,
    Course,
    Enrolled,
    Chapter,
    Customizable_reaction,
    Security_question,
    Quiz_history
    )

from pyramid.security import (
    remember,
    forget,
    )

from ..security import checkCredentials, getHash, group_security

import os
import sys
import random
import uuid
import bcrypt
#import base64
import datetime
#sys.path.append('../python')
#sys.path.append('./indigo-python-1.2.1-linux')
import rxn
import chem
import draw
from ..catalog import Catalog
import copy
import re




# Create a catalog object upon loading this module
# Let's not use 'global' keyword in functions since we should not be
# modifying this anyway.
#cat = Catalog()

# Experiment
# A dictionary from a unique identifying string (timestamp?) to an object
# containing the reaction image without reactants, and a set of possible answer images,
# complete with boolean flags to indicate whether they are right or wrong
quiz_problems = {}

current_user = {}


# Experiment
# student_id -> list of all past quiz problems, labeled as correct/incorrect/incomplete
# create an entry for student & problem when the problem is generated;
# update flags of the entry when an answer is received
history = {}
# Future work: store this in a DB for persistence
# Unrelated note to self: add a 'dismiss' button to skip a problem


def logged_layout():
    renderer = get_renderer("ltefserver:templates/logged_layout.pt")
    layout = renderer.implementation().macros['logged_layout']
    return layout






@view_config(route_name='manageusers', renderer='ltefserver:templates/new/manageusers.pt', permission='dominate')
def manageusers_view(request):

    message = ""
    group = group_security(request.authenticated_userid)
    custom_scripts = []
    custom_scripts.append("/bootstrap/js/manageusers.js")
    if 'addform.submitted' in request.params:
        # TODO: add checks for valid input
        u = request.params['username']
	firstname = request.params['first_name']
	lastname = request.params['last_name']
	id = request.params['id_number']
	email = request.params['email']
        g = request.params['group']
        p = request.params['password']
	password_confirm = request.params['confirm_password']

	if p == password_confirm:
             if DBSession.query(User).filter_by(username=u).first() is None:
                DBSession.add(User(username=u, group=g,firstname=firstname, lastname=lastname, studentNumber=id, email=email, phash=getHash(p)))
                message = "User '" + u + "' has been added"
             else:
                message = "User '" + u + "' already exists"

                #return HTTPFound(location = request.route_url('manageusers'))
	else:
	     message = "Passwords do not match"


    elif 'editform.username' in request.params:
        u = request.params['editform.username']
        # apply changes
        if request.params['editOption'] == 'password':
            DBSession.query(User).filter(User.username == u).update({"phash": getHash(request.params['password'])})
            message = "Password changed for user '" + u + "'"

        elif request.params['editOption'] == 'group':
            if not u == User.ADMIN and not u == User.GUEST:
                DBSession.query(User).filter(User.username == u).update({"group": request.params['group']})
                message = "User '" + u + "' has been reassigned to another group"
            else:
                message = "User '" + u + "' cannot be reassigned to another group"

        elif request.params['editOption'] == 'erase':
            # NOTE: update this logic as user data spreads through database
            if not u == User.ADMIN and not u == User.GUEST:
                DBSession.query(User).filter(User.username == u).delete()
                message = "User '" + u + "' has been permanently erased"
            else:
                message = "User '" + u + "' cannot be erased"

        #return HTTPFound(location = request.route_url('manageusers'))

    admins = DBSession.query(User,Group).filter(User.group==Group.id).filter(Group.desc==Group.ADMIN).all()
    teachers = DBSession.query(User,Group).filter(User.group==Group.id).filter(Group.desc==Group.TEACHER).all()
    students = DBSession.query(User,Group).filter(User.group==Group.id).filter(Group.desc==Group.STUDENT).all()
    guests = DBSession.query(User,Group).filter(User.group==Group.id).filter(Group.desc==Group.GUEST).all()

    groups = DBSession.query(Group).all()

    current_user = User.current_user(request.authenticated_userid)

    owner_courses = []
    enrolled_courses = []
    if group["is_teacher"]:
        owner_courses = Course.owner_courses(request.authenticated_userid)
    elif group["is_student"]:
        enrolled_courses = Enrolled.enrolled_courses(request.authenticated_userid)

    return {"layout" : logged_layout(),
            "logged_in" : current_user.firstname.title() + " " + current_user.lastname.title(),
            "admins" :  admins, "teachers" : teachers, "students" : students, "guests" : guests,
            "is_admin" : group["is_admin"], "is_teacher" : group["is_teacher"], "is_student" : group["is_student"],
            "groups" : groups,
  	         "custom_scripts" : custom_scripts,
            "message" : message,
	        "page_title" : "Manage Users",
            "owner_courses" : owner_courses,
            "enrolled_courses" : enrolled_courses,
            }
