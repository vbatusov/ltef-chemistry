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



def site_layout():
    renderer = get_renderer("ltefserver:templates/layout.pt")
    layout = renderer.implementation().macros['layout']
    return layout

def logged_layout():
    renderer = get_renderer("ltefserver:templates/logged_layout.pt")
    layout = renderer.implementation().macros['logged_layout']
    return layout

@view_config(route_name='managelists', renderer='ltefserver:templates/new/managelists.pt', permission='educate')
def managelists_view(request):
    message = ""
    group = group_security(request.authenticated_userid)
    user = DBSession.query(User).filter(User.username == request.authenticated_userid).first()
    custom_scripts = []

    if 'btnDiscard' in request.params: # from editlist
        message = "No changes made"

    elif 'btnSave' in request.params and request.params["txtTitle"] != "": # from editlist
        # If list.title exists, update DB
        # If not, add a new List entry
        newlist = [int(x) for x in request.params["listOfIDs"].split()]
        tit = request.params["txtTitle"]

        # Create a new list
        if "isNew" in request.params:
            if DBSession.query(List).filter_by(title=tit).first() is None:
                DBSession.add(List(owner=user.id, title=tit,\
                    desc=request.params["txtDesc"], data=newlist))
                message = "List '" + tit + "' has been created"
            else:
                message = "List '" + tit + "' already exists; no changes made"
        # Update existing list
        else:
            if tit == List.ALL_TITLE:
                message = "List '" + tit + "' is locked and cannot be edited"
            else:
                if DBSession.query(List).filter_by(title=tit).first() is not None:
                    DBSession.query(List).filter_by(title=tit)\
                        .update({"title" : tit, "desc" : request.params["txtDesc"], "data" : newlist})
                    message = "List '" + tit + "' has been updated"
                else:
                    # This cannot occur
                    message = "Error: Editing a list that cannot be found in the database!"

    elif 'btnRemove' in request.params:
        tit = request.params["txtTitle"]

        if tit == List.ALL_TITLE:
            message = "List '" + tit + "' is locked and cannot be removed"
        else:
            DBSession.query(List).filter_by(title=tit).delete()
            message = "List '" + tit + "' has been permanently removed"

    user = DBSession.query(User).filter(User.username == request.authenticated_userid).first()
    lists = []
    if user is not None:
        lists = [(l.title, l.desc) for l in DBSession.query(List).filter(List.owner == user.id).all()]

    owner_courses = []
    enrolled_courses = []
    if group["is_teacher"]:
        owner_courses = Course.owner_courses(request.authenticated_userid)
    elif group["is_student"]:
        enrolled_courses = Enrolled.enrolled_courses(request.authenticated_userid)

    return {"layout" : logged_layout(),
            "custom_scripts" : custom_scripts,
	        "logged_in" : request.authenticated_userid,
            "lists" : lists,
            "is_admin" : group["is_admin"], "is_teacher" : group["is_teacher"], "is_student" : group["is_student"],
            "message" : message,
	        "page_title" : "Manage Reaction Lists",
            "owner_courses" : owner_courses,
            "enrolled_courses" : enrolled_courses,
            }

def student_courses(request):

    currentuser = DBSession.query(User).filter(User.username == request.authenticated_userid).first()
    student_courses = DBSession.query(Course,Enrolled).filter(Course.id==Enrolled.courseid).filter(Enrolled.userid==currentuser.id).all()
    group = group_security(request.authenticated_userid)

    if len(student_courses) == 0 and group["is_student"]  :
        url = request.route_url("course_signup")
        return HTTPFound(location=url)
    else:
        return student_courses


@view_config(route_name='synthesis', renderer='ltefserver:templates/new/synthesis.pt', permission='study')
def synthesis_view(request):
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
            "is_admin" : group["is_admin"], "is_teacher" : group["is_teacher"], "is_student" : group["is_student"],
    	    "logged_in" : request.authenticated_userid,
    	    "page_title" : "Multistep Synthesis"	 }
