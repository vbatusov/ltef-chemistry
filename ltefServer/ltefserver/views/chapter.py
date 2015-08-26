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

@view_config(route_name='chapter_action', match_param='action=edit_chapter', renderer='ltefserver:templates/new/edit_chapter.pt', permission='educate')
def edit_chapter_view(request):


    basename = request.matchdict["basename"]
    chapter_name = request.matchdict["chapter"]
    custom_scripts = []
    message = ""
    chapter_title = ""
    course_description = ""
    currentuser = DBSession.query(User).filter(User.username == request.authenticated_userid).first()
    chapters =  DBSession.query(Course, Chapter).filter(Course.owner == currentuser.id).filter(Chapter.course == Course.id ).all()
    group = group_security(request.authenticated_userid)

    current_chapter = DBSession.query(Chapter).filter(Course.owner == currentuser.id).filter(Chapter.course == Course.id ).filter(Chapter.title == chapter_name).first()

    if 'submit.edit_chapter' in request.params:

         chapter_title = request.params['chapter_title']
         chapter_description = request.params['chapter_description']

         DBSession.query(Chapter).filter(Chapter.id == current_chapter.id).update({"title": chapter_title, "description": chapter_description })
         message = "Chapter " + chapter_title + " already exists"

         return HTTPFound(location=request.route_url('home') + 'class/' + basename )

    owner_courses = []
    enrolled_courses = []
    if group["is_teacher"]:
        owner_courses = Course.owner_courses(request.authenticated_userid)
    elif group["is_student"]:
        enrolled_courses = Enrolled.enrolled_courses(request.authenticated_userid)

    return {"layout": logged_layout(),
            "logged_in" : request.authenticated_userid,
            "message" : message,
            "custom_scripts" : custom_scripts,
            "is_admin" : group["is_admin"], "is_teacher" : group["is_teacher"], "is_student" : group["is_student"],
            "chapters" : chapters,
            "owner_courses" : owner_courses,
            "enrolled_courses" : enrolled_courses,
	    "current_chapter" : current_chapter,
            "page_title" : "Edit Chapter " + chapter_name    }


@view_config(route_name='chapter_action', match_param='action=remove_chapter', permission='educate')
def remove_chapter_view(request):


    basename = request.matchdict["basename"]
    chapter_name = request.matchdict["chapter"]
    custom_scripts = []
    message = ""
    chapter_title = ""
    course_description = ""
    currentuser = DBSession.query(User).filter(User.username == request.authenticated_userid).first()
    group = group_security(request.authenticated_userid)

    current_chapter = DBSession.query(Chapter).filter(Course.owner == currentuser.id).filter(Chapter.course == Course.id ).filter(Chapter.title == chapter_name).first()

    DBSession.query(Chapter).filter(Chapter.id == current_chapter.id).delete()
    DBSession.query(Customizable_reaction).filter(Customizable_reaction.chapter == current_chapter.id).delete()

    return HTTPFound(location=request.route_url('home') + 'class/' + basename )



@view_config(route_name='chapter_action', match_param='action=add_selectable_reaction',  renderer='ltefserver:templates/new/add_selectable_reaction.pt', permission='educate')
def add_selectable_reaction_view(request):

    message = ""
    customizable_title = ""
    customizable_description = ""
    reaction = ""
    custom_scripts = []
    group = group_security(request.authenticated_userid)
    basename = request.matchdict["basename"]
    chapter_name = request.matchdict["chapter"]
    currentuser = DBSession.query(User).filter(User.username == request.authenticated_userid).first()
    chapter =  DBSession.query(Chapter).filter(Course.owner == currentuser.id).filter(Course.name == basename).filter(Chapter.course == Course.id).filter(Chapter.title == chapter_name ).first()

    owner_courses = []
    enrolled_courses = []

    customizable_reaction = DBSession.query(Reac).filter(Customizable_reaction.chapter == chapter.id).filter().all()

    if 'submit.reaction.addanother' in request.params:
        if 'reaction' in request.params:
            reaction_id = request.params['reaction']
            customizable_title = request.params['reaction_title']
            customizable_description = request.params['reaction_description']
            reaction = DBSession.query(Reac).filter(reaction_id == Reac.id).first()

        	# if both description and title have inputs then add them
            if len(customizable_title) > 0 and len(customizable_description) > 0:
        	    customizable_title = request.params['reaction_title']
        	    customizable_description = request.params['reaction_description']
        	    DBSession.add(Customizable_reaction( reaction=reaction_id, chapter=chapter.id,  title=customizable_title, description=customizable_description))
        	    message = "Successfully added reaction title and description"

            elif len(customizable_title) > 0:
        	    customizable_title = request.params['reaction_title']
        	    DBSession.add(Customizable_reaction( reaction=reaction_id, chapter=chapter.id, description=reaction.description,  title=customizable_title))
        	    message = "Successfully added reaction only title"

            elif len(customizable_description) > 0:
        	    customizable_description = request.params['reaction_description']
        	    DBSession.add(Customizable_reaction( reaction=reaction_id, title=reaction.full_name, chapter=chapter.id, description=customizable_description))
        	    message = "Successfully added reaction with only description"

            else:
                DBSession.add(Customizable_reaction( reaction=reaction_id , title=reaction.full_name, description=reaction.description, chapter=chapter.id))
                message = "All default"
        else:
            message = "Missing Reaction"

    elif 'submit.reaction.finish' in request.params:
        message = "Finished"
        return HTTPFound(location=request.route_url('home') + 'class/' + basename )

    if group["is_teacher"]:
        owner_courses = Course.owner_courses(request.authenticated_userid)
    elif group["is_student"]:
        enrolled_courses = Enrolled.enrolled_courses(request.authenticated_userid)

    select_reactions = DBSession.query(Reac.full_name, Reac.id).except_(DBSession.query(Reac.full_name, Reac.id).filter(Customizable_reaction.chapter == chapter.id).filter(Reac.id == Customizable_reaction.reaction)).order_by(Reac.full_name).all()

    return {"layout": logged_layout(),
            "logged_in" : request.authenticated_userid,
	        "is_admin" : group["is_admin"], "is_teacher" : group["is_teacher"], "is_student" : group["is_student"],
	        "page_title" : "Add Selectable Reaction",
            "leftbox" : select_reactions,
	        "custom_scripts" : custom_scripts,
	        "message" : message,
	        "basename" : basename,
            "owner_courses" : owner_courses,
            "enrolled_courses" : enrolled_courses,
            "chapter" : chapter_name,
            }
