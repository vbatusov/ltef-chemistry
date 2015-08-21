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
cat = Catalog()

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



@view_config(route_name='home', renderer='ltefserver:templates/new/home.pt', permission='study')
def home_view(request):
    #print "Home view fired up, authenticated_userid is " + str(request.authenticated_userid)
    message = ""
    custom_scripts = []

    currentuser = DBSession.query(User).filter(User.username == request.authenticated_userid).first()
    teacher_courses = DBSession.query(Course).filter(Course.owner == currentuser.id).all()
    group = group_security(request.authenticated_userid)

    student_courses = DBSession.query(Course,Enrolled).filter(Course.id==Enrolled.courseid).filter(Enrolled.userid==currentuser.id).all()
    group = group_security(request.authenticated_userid)

    if len(student_courses) == 0 and group["is_student"]:
        url = request.route_url("add_course")
        return HTTPFound(location=url)

    owner_courses = []
    enrolled_courses = []
    if group["is_teacher"]:
        owner_courses = Course.owner_courses(request.authenticated_userid)
    elif group["is_student"]:
	enrolled_courses = Enrolled.enrolled_courses(request.authenticated_userid)

    return {"layout" : logged_layout(),
	    "owner_courses" : owner_courses,
 	    "enrolled_courses" : enrolled_courses,
            "custom_scripts" : custom_scripts,
            "base_to_full" : cat.base_to_full,
            "logged_in" : request.authenticated_userid,
	    "teacher_courses" : teacher_courses,
	    "student_courses" : student_courses,
            "is_admin" : group["is_admin"], "is_teacher" : group["is_teacher"], "is_student" : group["is_student"],
            "page_title" : "Overview",
	    "message" : message
	    }
