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


@view_config(route_name='addreaction', renderer='ltefserver:templates/new/addreaction.pt', permission='study')
def addreaction_view(request):
    custom_scripts = []
    group = group_security(request.authenticated_userid)

    owner_courses = []
    enrolled_courses = []
    if group["is_teacher"]:
        owner_courses = Course.owner_courses(request.authenticated_userid)
    elif group["is_student"]:
        enrolled_courses = Enrolled.enrolled_courses(request.authenticated_userid)

    return {"layout": logged_layout(),
	       "custom_scripts" : custom_scripts,
            "owner_courses" : owner_courses,
            "enrolled_courses" : enrolled_courses,
            "logged_in" : request.authenticated_userid,
            "is_admin" : group["is_admin"], "is_teacher" : group["is_teacher"], "is_student" : group["is_student"],
	        "page_title" : "Add New Reaction"			 }






@view_config(route_name='editlist', renderer='ltefserver:templates/new/editlist.pt', permission='educate')
def editlist_view(request):

    message = ""
    title = ""
    desc = ""
    new = True
    # Data for select boxes: lists of pairs (full reaction name, reaction id)
    leftbox = []
    rightbox = []
    custom_scripts=""
    group = group_security(request.authenticated_userid)

    if 'editlistformtitle' in request.params:
        list_title = request.params['editlistformtitle']
        mylist = DBSession.query(List).filter(List.title == list_title).first()
        title = mylist.title
        desc = mylist.desc
        (leftbox, rightbox) = cat.get_selectbox_lists_by_list_id(mylist.id)
        new = False
    else:
        list_title = List.ALL_TITLE
        list_id = DBSession.query(List).filter(List.title == list_title).first().id
        (rightbox, leftbox) = cat.get_selectbox_lists_by_list_id(list_id)

    if title == List.ALL_TITLE:
        message = "This list is locked and cannot be changed"

    owner_courses = []
    enrolled_courses = []
    if group["is_teacher"]:
        owner_courses = Course.owner_courses(request.authenticated_userid)
    elif group["is_student"]:
        enrolled_courses = Enrolled.enrolled_courses(request.authenticated_userid)

    return {"layout" : logged_layout(),
            "logged_in" : request.authenticated_userid,
            "message" : message,
            "title" : title,
            "desc" : desc,
            "leftbox" : leftbox,
            "rightbox" : rightbox,
            "new" : new,
	        "custom_scripts" : custom_scripts,
 	        "is_admin" : group["is_admin"], "is_teacher" : group["is_teacher"], "is_student" : group["is_student"],
	        "page_title" : "Manage Reaction Lists",
            "owner_courses" : owner_courses,
            "enrolled_courses" : enrolled_courses,
            }
