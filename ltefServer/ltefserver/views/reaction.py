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


@view_config(route_name='reaction_action', match_param='action=edit_reaction', renderer='ltefserver:templates/new/edit_selectable_reaction.pt', permission='educate')
def edit_reaction_view(request):

    # retrieve all match dictionary
    course_name = request.matchdict["course"]
    chapter_name = request.matchdict["chapter"]
    reaction_name = request.matchdict["reaction"]

    # warning message
    message = ""

    # retrieve current user
    currentuser = DBSession.query(User).filter(User.username == request.authenticated_userid).first()

    #add an custom scripts
    custom_scripts = []

    # retrieve the users permission group and retieve the users courses
    group = group_security(request.authenticated_userid)
    owner_courses = []
    enrolled_courses = []
    if group["is_teacher"]:
        owner_courses = Course.owner_courses(request.authenticated_userid)
    elif group["is_student"]:
        enrolled_courses = Enrolled.enrolled_courses(request.authenticated_userid)

    # retrieve customizable reaction
    current_chapter = DBSession.query(Chapter).filter(Course.owner == currentuser.id).filter(Course.name == course_name).filter(Chapter.course == Course.id ).filter(Chapter.title == chapter_name).first()
    reaction = DBSession.query(Reac).filter(Reac.basename == reaction_name).first()
    customizable_reaction = DBSession.query(Customizable_reaction).filter(Customizable_reaction.reaction == reaction.id).filter(Customizable_reaction.chapter == current_chapter.id).first()

    # filable raction value, reaction basename, reaction title, and reaction description.
    reaction_value = customizable_reaction.reaction
    reaction_title = customizable_reaction.title
    reaction_description = customizable_reaction.description
    # All the current information needs to be displayed in the in boxes

    if 'submit.reaction.finish' in request.params:

        customizable_title = request.params['reaction_title']
        customizable_description = request.params['reaction_description']

        if len(customizable_title) > 0 and len(customizable_description) > 0:
            DBSession.query(Customizable_reaction).filter(Customizable_reaction.id == customizable_reaction.id).update({ "title":customizable_title,  "description":customizable_description })

            return HTTPFound(location=request.route_url('home') + 'class/' + course_name)
        else:
            message = "Both inputs are required"

    return {"layout": logged_layout(),
	        "custom_scripts" : custom_scripts,
            "message" : message,
            "owner_courses" : owner_courses,
            "enrolled_courses" : enrolled_courses,
            "logged_in" : request.authenticated_userid,
            "is_admin" : group["is_admin"], "is_teacher" : group["is_teacher"], "is_student" : group["is_student"],
	        "page_title" : "Edit Reaction",
            "course_name" : course_name,
            "chapter_name" : chapter_name ,
            "reaction_name" : reaction_name,
            "reaction_title" : reaction_title,
            "reaction_description" : reaction_description,
            }





@view_config(route_name='reaction_action', match_param='action=remove_reaction', permission='educate')
def remove_reaction_view(request):

    # retrieve all match dictionary
    course_name = request.matchdict["course"]
    chapter_name = request.matchdict["chapter"]
    reaction_name = request.matchdict["reaction"]

    # retrieve current user
    currentuser = DBSession.query(User).filter(User.username == request.authenticated_userid).first()

    # retrieve customizable reaction
    current_chapter = DBSession.query(Chapter).filter(Course.owner == currentuser.id).filter(Course.name == course_name).filter(Chapter.course == Course.id ).filter(Chapter.title == chapter_name).first()
    reaction = DBSession.query(Reac).filter(Reac.basename == reaction_name).first()
    customizable_reaction = DBSession.query(Customizable_reaction).filter(Customizable_reaction.reaction == reaction.id).filter(Customizable_reaction.chapter == current_chapter.id).first()

    # remove customizable reaction
    DBSession.query(Customizable_reaction).filter(Customizable_reaction.id == customizable_reaction.id).delete()

    # return user back to the course home page
    return HTTPFound(location=request.route_url('home') + 'class/' + course_name)


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
