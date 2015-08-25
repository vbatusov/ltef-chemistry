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
from ..security import checkCredentials, getHash

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

def main_layout():
    renderer = get_renderer("ltefserver:templates/main_layout.pt")
    layout = renderer.implementation().macros['main_layout']
    return layout


@view_config(route_name='student_register', renderer='ltefserver:templates/new/student_register.pt')
def student_register_view(request):


    message= ""
    username = ""
    first_name = ""
    last_name = ""
    student_number = ""
    email = ""
    password = ""
    confirm_password = ""
    question = ""
    answer = ""


    if 'form_register.submitted' in request.params:
        first_name = request.params['first_name']
	username = request.params['username']
        last_name = request.params['last_name']
  	student_number = request.params['student_number']
	email = request.params['email']
	password = request.params['password']
	confirm_password = request.params['confirm_password']
	security_question = request.params['security_question']
        security_answer = request.params['security_answer']

	if len(first_name) <= 0 & len(last_name) <= 0 & len(security_question) <= 0 & len(security_answer) <= 0 & len(password) <= 0 & len(confirm_password) <= 0 :
		message = "Missing inputs"
	else:
	    if password <> confirm_password:
		 message = "Passwords are not matching"
	    else:
		# Check if there are no existing usernames
		if DBSession.query(User).filter_by(username=username).first() is None:
            	    if DBSession.query(User).filter_by(email=email).first() is None:
		        DBSession.add(User(username=username, email=email, firstname=first_name, lastname=last_name, group=4, studentNumber=student_number, phash=getHash(password)))

			current_user = User.current_user(username)

			DBSession.add(Security_question(user=current_user.id, question=security_question, answer = security_answer ))
            	        message = "User '" + username + "' has been added"
			if checkCredentials(username, password):
		            headers = remember(request, username)
			    print "Logged in as " + username + "; creating a blank history"
            		    history[username] = []
            		    current_user = request.params
	    		    came_from = request.params.get('came_from', '/')
			    return HTTPFound(location = came_from, headers = headers)

		    else:
			message = "Email '" + email + "' already exists"
        	else:
            	    message = "Username '" + username + "' already exists"
    return {"layout": main_layout(),
	    "message": message
	   }

@view_config(route_name='select_register', renderer='ltefserver:templates/new/select_register.pt')
def select_register_view(request):
    return {"layout": main_layout()
            }

@view_config(route_name='password_reset', renderer='ltefserver:templates/new/password_reset.pt')
def password_reset_view(request):

    message = ""
    email= ""

    if 'email' in request.params:
        email = request.params['email']

	if DBSession.query(User).filter(User.email == email).first() is None:
	    message = "Sorry but that email address is not in our records, please try again."
        else:
            user =  DBSession.query(User).filter(User.email == email).first()
            return HTTPFound(location=request.route_url('security_question', _query={'email':user.email}))


    return {"layout": main_layout(),
            "message" : message
	     }


@view_config(route_name='security_question', renderer='ltefserver:templates/new/security_question.pt')
def security_question_view(request):

    message = ""
    email = ""
    question = ""

    if 'email' in request.params:
        email = request.params['email']

        if 'answer' in request.params:
	    answer = request.params['answer']

            if DBSession.query(User).filter(User.email == email).first() is None:

                return HTTPFound(loddcation=request.route_url('password_reset'))

            elif DBSession.query(Security_question).filter(User.email == email).filter(Security_question.answer == answer).filter(User.id == Security_question.user).first() is None:

                user =  DBSession.query(User).filter(User.email == email).first()
                security_question = DBSession.query(Security_question).filter(user.id == Security_question.user).first()
                question = security_question.question

                return {"layout" : main_layout(),
                        "message" : "Incorrect Answer",
                        "question" : question,
                         }
            else:
                return HTTPFound(location=request.route_url('reset_password', _query={'email' : email, 'answer' : answer }))


	if DBSession.query(User).filter(User.email == email).first() is None:

	   return HTTPFound(location=request.route_url('password_reset'))
	else:
	    user =  DBSession.query(User).filter(User.email == email).first()
	    security_question = DBSession.query(Security_question).filter(user.id == Security_question.user).first()
	    question = security_question.question
    else:
        return HTTPFound(location=request.route_url('password_reset'))


    return {"layout" : main_layout(),
	    "message" : message,
	    "question" : question,
	    "email" : email,
	   }


@view_config(route_name='reset_password', renderer='ltefserver:templates/new/reset_password.pt')
def reset_password_view(request):

    email = ""
    answer = ""
    message = ""
    password = ""
    confirm_password =""

    if ('email' in request.params) & ('answer' in request.params):
        email = request.params['email']
        answer = request.params['answer']

	     # Update password
        if('confirm_password' in request.params) & ('password' in request.params):
            confirm_password = request.params['confirm_password']
	    password = request.params['password']

	    if DBSession.query(Security_question).filter(User.email == email).filter(Security_question.answer == answer).filter(User.id == Security_question.user).first() is None:
	        return HTTPFound(location=request.route_url('home'))
	    else:
	        if password <> confirm_password:
		    message = "Both passwords don't match. Please try again. "
		else:

		    DBSession.query(User).filter(User.email == email).update({"phash": getHash(password)})
		    return HTTPFound(location=request.route_url('login'))

    else:
        return HTTPFound(location=request.route_url('password_reset'))

    return { "layout" : main_layout(),
             "message" : message,
	         "email" : email,
	         "answer" : answer,
	       }


@view_config(route_name='add_secret_question', renderer='ltefserver:templates/new/add_secret_question.pt')
def add_secret_question(request):

    message = ""

    return{"layout" : main_layout(),
	       "message" : message
    	  }


@view_config(route_name='add_course', renderer='ltefserver:templates/new/add_course.pt')
def add_course_view(request):

    message = ""
    access_code = ""
    currentuser = DBSession.query(User).filter(User.username == request.authenticated_userid).first()

    enrolls = DBSession.query(Enrolled).filter(Enrolled.userid == currentuser.id ).all()
    student_courses =  DBSession.query(Course,Enrolled,User).filter(Course.id==Enrolled.courseid).filter(Enrolled.userid==currentuser.id).filter(Course.id==User.id).all()

    if 'submit.coursesignup' in request.params:
        access_code = request.params['access_code']

        if DBSession.query(Course).filter_by(access_code=access_code).first() is None:
                message = "Invalid access code"
        else:

            course_id = DBSession.query(Course).filter(Course.access_code == access_code ).first()
            if DBSession.query(Enrolled).filter(Enrolled.userid==currentuser.id).filter(Enrolled.courseid==course_id.id ).first() is None:

                course = DBSession.query(Course).filter_by(access_code=access_code).first()
                DBSession.add(Enrolled(userid=currentuser.id, courseid=course.id))
                student_courses = DBSession.query(Course,Enrolled,User).filter(Course.id==Enrolled.courseid).filter(Enrolled.userid==currentuser.id).filter(Course.id==User.id).all()
                if len(student_courses) == 1:
                    return HTTPFound(location = request.route_url('home'))


    return {"layout": main_layout(),
            "message": message
	       }


@view_config(route_name='login', renderer='ltefserver:templates/new/login.pt')
@forbidden_view_config(renderer='ltefserver:templates/new/login.pt')
def login(request):

    login_url = request.route_url('login')
    referrer = request.url
    if referrer == login_url:
        referrer = '/' # never use the login form itself as came_from
    came_from = request.params.get('came_from', referrer)
    message = ''
    login = ''
    password = ''
    if 'form.submitted' in request.params:
        login = request.params['login']
        password = request.params['password']
        if checkCredentials(login, password):
            headers = remember(request, login)


            print "Logged in as " + login + "; creating a blank history"
            history[login] = []
	    current_user = request.params
            return HTTPFound(location = came_from,
                             headers = headers)
        message = 'Incorrect username or password.'

    return dict(
        layout = main_layout(),
     	message = message,
        url = request.application_url + '/login',
        came_from = came_from,
        login = login,
        password = password,
        )

@view_config(route_name='logout')
def logout(request):
    headers = forget(request)
    return HTTPFound(location = request.route_url('home'),
                     headers = headers)
