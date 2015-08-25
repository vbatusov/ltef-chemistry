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



@view_config(route_name='contact', renderer='ltefserver:templates/new/contact.pt', permission='study')
def contact_view(request):
    group = group_security(request.authenticated_userid)
    custom_scripts = []
    state = "new form"
    if "txtComment" in request.POST:
        state = "sent"
        with open("contact.txt", "a") as myfile:
            myfile.write(str(datetime.datetime.now()) + "\n")
            myfile.write("-------MESSAGE--------\n")
            myfile.write(request.POST["txtComment"] + "\n")
            myfile.write("----END OF MESSAGE----\n\n")

    owner_courses = []
    enrolled_courses = []
    if group["is_teacher"]:
        owner_courses = Course.owner_courses(request.authenticated_userid)
    elif group["is_student"]:
        enrolled_courses = Enrolled.enrolled_courses(request.authenticated_userid)

    return {"layout": logged_layout(),
            "custom_scripts" : custom_scripts,
            "state" : state,
            "is_admin" : group["is_admin"], "is_teacher" : group["is_teacher"], "is_student" : group["is_student"],
	        "logged_in" : request.authenticated_userid,
            "owner_courses" : owner_courses,
            "enrolled_courses" : enrolled_courses,
	        "page_title" : "Contact Us"			}

@view_config(route_name='edit_account', renderer='ltefserver:templates/new/edit_account.pt', permission='study')
def edit_account_view(request):
    group = group_security(request.authenticated_userid)
    custom_scripts = []
    owner_courses = []
    enrolled_courses = []
    current_user = User.current_user(request.authenticated_userid)

    firstname = ""
    lastname = ""
    email = ""
    id_number = ""

    old_password = ""
    new_password = ""
    confirm_password = ""

    reset_password_message = ""
    update_account_message = ""

    if group["is_teacher"]:
        owner_courses = Course.owner_courses(request.authenticated_userid)
    elif group["is_student"]:
        enrolled_courses = Enrolled.enrolled_courses(request.authenticated_userid)

    if 'update.account.submitted' in request.params:
        firstname = request.params['firstname']
        lastname = request.params['lastname']
        email = request.params['email']
        id_number = request.params['studentNumber']

        if (DBSession.query(User).filter(User.email == email).first() is None) & (current_user.email <> email):
            DBSession.query(User).filter(User.id == current_user.id).update({"firstname": firstname, "lastname": lastname, "studentNumber": id_number, "email": email })
            update_account_message = "Account Updated"
        elif current_user.email == email:
            DBSession.query(User).filter(User.id == current_user.id).update({"firstname": firstname, "lastname": lastname, "studentNumber": id_number })
            update_account_message = "Account Updated"
        else:
            update_account_message = "Email " + str(email) + " is already registered"


    if 'reset_password.submit' in request.params:
        old_password = request.params['old_password']
        new_password = request.params['new_password']
        confirm_password = request.params['confirm_password']

        if checkCredentials(current_user.username, old_password):
            if new_password <> confirm_password:
    		    reset_password_message = "Passwords are not matching"
    	    else:
                DBSession.query(User).filter(User.id == current_user.id).update({"phash" : getHash(new_password) })
                reset_password_message = "Password has been updated"
        else:
            reset_password_message = "Old password does not match"

    return {"layout": logged_layout(),
            "custom_scripts" : custom_scripts,
            "is_admin" : group["is_admin"], "is_teacher" : group["is_teacher"], "is_student" : group["is_student"],
            "logged_in" : request.authenticated_userid,
            "owner_courses" : owner_courses,
            "enrolled_courses" : enrolled_courses,
            "page_title" : "Edit Account",
	        "current_user" : current_user,
            "reset_password_message" : reset_password_message,
            "update_account_message" : update_account_message
	     }



@view_config(route_name='about', renderer='ltefserver:templates/new/about.pt', permission='study')
def about_view(request):
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
     	    "page_title" : "About Us"		}
