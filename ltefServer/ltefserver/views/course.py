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

@view_config(route_name='class_action',  match_param='action=edit_course', renderer='ltefserver:templates/new/edit_course.pt', permission='educate')
def course_edit_view(request):

    basename = ""
    course_name = ""
    course_description = ""
    course = ""
    message = ""
    custom_scripts = []
    owner_courses = []
    enrolled_courses = []

    group = group_security(request.authenticated_userid)
    current_user = DBSession.query(User).filter(User.username == request.authenticated_userid).first()
    basename = request.matchdict["basename"]

    if group["is_teacher"]:
        owner_courses = Course.owner_courses(request.authenticated_userid)
        course = DBSession.query(Course).filter(Course.name == basename).filter(Course.owner==current_user.id).first()
    elif group["is_student"]:
        enrolled_courses = Enrolled.enrolled_courses(request.authenticated_userid)

    if 'submit.edit.course' in request.params:
        course_name = request.params['course_name']
        course_description =  request.params['course_description']
        course_edit = DBSession.query(Course).filter(Course.name == course_name).filter(Course.owner == current_user.id).first()
        # The teacher cannot update the course name to the same one that already exist
        if (course_edit is None) & (len(course_name) > 0):
            DBSession.query(Course).filter(Course.id == course.id).update({"name":course_name, "description":course_description })

            return HTTPFound(location=request.route_url('home') )

        elif course_edit.name == request.params['course_name']:

            course_description =  request.params['course_description']
            DBSession.query(Course).filter(Course.id == course.id).update({ "description":course_description })

            return HTTPFound(location=request.route_url('home') )

        elif len(course_name) == 0:
            message = "Class Title connot be empty"
        else:
            message = "Class Title " + course_name + " already exists"

    return {"layout": logged_layout(),
            "custom_scripts" : custom_scripts,
	        "course" : course,
	        "basename" : basename,
            "owner_courses" : owner_courses,
            "enrolled_courses" : enrolled_courses,
	        "logged_in" : request.authenticated_userid,
            "is_admin" : group["is_admin"], "is_teacher" : group["is_teacher"], "is_student" : group["is_student"],
            "page_title" : "Edit " + basename,
            "message" : message  }

@view_config(route_name='class', renderer='ltefserver:templates/new/course.pt', permission='study')
def course_view(request):
    basename = ""
    custom_scripts = []
    group = group_security(request.authenticated_userid)

    currentuser = DBSession.query(User).filter(User.username == request.authenticated_userid).first()
    basename = request.matchdict["basename"]
    quiz_histories = []
    if group["is_teacher"]:
    	students =  DBSession.query(Course,Enrolled,User).filter(Course.name == basename).filter(Course.id==Enrolled.courseid).filter(Course.owner==currentuser.id).filter(User.id == Enrolled.userid).all()
    	chapters =  DBSession.query(Course, Chapter).filter(Course.owner == currentuser.id).filter(Chapter.course == Course.id ).filter(Course.name == basename).all()
    	course = DBSession.query(Course).filter(Course.name == basename).filter(Course.owner==currentuser.id).first()

    elif group["is_student"]:
        students = []
        chapters = DBSession.query(Course, Chapter).filter(Enrolled.userid == currentuser.id).filter(Chapter.course == Course.id).filter(Course.name == basename).filter(Enrolled.courseid == Course.id).all()
        course = DBSession.query(Course).filter(Course.name == basename).filter(Enrolled.courseid == Course.id ).filter(Enrolled.userid == currentuser.id  ).first()
        quiz_histories = DBSession.query(Quiz_history, Chapter, Course, User).filter(Quiz_history.user == currentuser.id).filter(User.id == currentuser.id).filter(Quiz_history.course == course.id).filter(Chapter.id == Quiz_history.chapter).all()


    customizable_reactions = {}

    for (course, chapter) in chapters:
        customizable_reactions[chapter.id] = DBSession.query(Customizable_reaction, Reac).filter(Customizable_reaction.chapter == chapter.id ).filter(Customizable_reaction.reaction == Reac.id).all()

    owner_courses = []
    enrolled_courses = []
    if group["is_teacher"]:
        owner_courses = Course.owner_courses(request.authenticated_userid)
    elif group["is_student"]:
        enrolled_courses = Enrolled.enrolled_courses(request.authenticated_userid)


    return {"layout": logged_layout(),
            "custom_scripts" : custom_scripts,
            "students" : students,
	        "course" : course,
	        "basename" : basename,
            "owner_courses" : owner_courses,
            "enrolled_courses" : enrolled_courses,
	        "quiz_histories" : quiz_histories,
	        "chapters" : chapters,
	        "customizable_reactions" : customizable_reactions,
	        "logged_in" : request.authenticated_userid,
            "is_admin" : group["is_admin"], "is_teacher" : group["is_teacher"], "is_student" : group["is_student"],
            "page_title" : basename  }



@view_config(route_name='class_action', match_param='action=create_chapter', renderer='ltefserver:templates/new/create_chapter.pt', permission='educate')
def create_chapter_view(request):


    course_name = request.matchdict["basename"]
    custom_scripts = []
    message = ""
    chapter_title = ""
    course_description = ""
    currentuser = DBSession.query(User).filter(User.username == request.authenticated_userid).first()
    chapters =  DBSession.query(Course, Chapter).filter(Course.owner == currentuser.id).filter(Chapter.course == Course.id ).all()
    group = group_security(request.authenticated_userid)

    if 'submit.create_chapter' in request.params:
         chapter_title = request.params['chapter_title']
         chapter_description = request.params['chapter_description']

         if DBSession.query(Chapter).filter(Chapter.title == chapter_title).filter(Chapter.course == Course.id ).filter(Course.name == course_name).filter(Course.owner == currentuser.id).first() is None:
               course = DBSession.query(Course).filter(Course.owner == currentuser.id).filter(Course.name == course_name ).first()
	       DBSession.add(Chapter(title=chapter_title, course=course.id, description=chapter_description))
	       chapters =  DBSession.query(Course, Chapter).filter(Course.owner == currentuser.id).filter(Chapter.course == Course.id ).all()
               message = "Chapter " + chapter_title + " has been added"

               return HTTPFound(location=request.route_url('home') + 'class/' + course_name )
         else:
               message = "Class Title " + chapter_title + " already exists"

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
            "page_title" : "Add Chapter"           }




@view_config(route_name='remove_student', permission='educate')
def remove_student_view(request):

    course_name = request.matchdict["course"]
    student_username = request.matchdict["student"]
    current_user = DBSession.query(User).filter(User.username == request.authenticated_userid).first()

    course = DBSession.query(Course).filter(Course.owner == current_user.id).filter(Course.name == course_name ).first()
    student = User.current_user(student_username)

    # Delete Enrolled Student from current course
    DBSession.query(Enrolled).filter(Enrolled.userid == student.id).filter(Enrolled.courseid == course.id).delete()

    return HTTPFound(location=request.route_url('home') + 'class/' + course_name )

@view_config(route_name='createcourse', renderer='ltefserver:templates/new/createcourse.pt', permission='educate')
def create_course_view(request):

    custom_scripts = []
    message = ""
    class_title = ""
    course_description = ""
    currentuser = DBSession.query(User).filter(User.username == request.authenticated_userid).first()
    courses = DBSession.query(Course).filter(Course.owner == currentuser.id).all()
    group = group_security(request.authenticated_userid)

    if 'submit.createcourse' in request.params:
	 class_title = request.params['class_title']
	 course_description = request.params['course_description']
	 new_course_code = str(uuid.uuid4())[0:16].upper()  # or whatever

	 if DBSession.query(Course).filter(Course.name == class_title).filter(Course.owner == currentuser.id).first() is None:
               DBSession.add(Course(name=class_title, owner=currentuser.id, description=course_description,  access_code=new_course_code))
               message = "Class " + class_title + " has been added"
               courses = DBSession.query(Course).filter(Course.owner == currentuser.id).all()
	 else:
               message = "Class Title " + class_title + " already exists"

    owner_courses = []
    enrolled_courses = []
    if group["is_teacher"]:
        owner_courses = Course.owner_courses(request.authenticated_userid)
    elif group["is_student"]:
        enrolled_courses = Enrolled.enrolled_courses(request.authenticated_userid)


    return {"layout": logged_layout(),
            "logged_in" : request.authenticated_userid,
            "owner_courses" : owner_courses,
	    "enrolled_courses" : enrolled_courses,
            "custom_scripts" : custom_scripts,
	    "message" : message,
            "custom_scripts" : custom_scripts,
	    "is_admin" : group["is_admin"], "is_teacher" : group["is_teacher"], "is_student" : group["is_student"],
	    "courses" : courses,
	    "page_title" : "Create Class"           }




@view_config(route_name='course_signup', renderer='ltefserver:templates/new/course_signup.pt', permission='study')
def course_signup_view(request):

    custom_scripts = []
    message = ""
    access_code = ""
    currentuser = DBSession.query(User).filter(User.username == request.authenticated_userid).first()
    group = group_security(request.authenticated_userid)


    enrolls = DBSession.query(Enrolled).filter(Enrolled.userid == currentuser.id ).all()
    student_courses =  DBSession.query(Course,Enrolled,User).filter(Course.id==Enrolled.courseid).filter(Enrolled.userid==currentuser.id).filter(Course.id==User.id).all()

    if len(student_courses) == 0 :
  	message = "To enroll in a course, please provide the course key below."

    if 'submit.coursesignup' in request.params:
	access_code = request.params['access_code']
	print access_code
	message = access_code

	if DBSession.query(Course).filter_by(access_code=access_code).first() is None:
		message = "Invalid access code"
   	else:

	    course_id = DBSession.query(Course).filter(Course.access_code == access_code ).first()
            if DBSession.query(Enrolled).filter(Enrolled.userid==currentuser.id).filter(Enrolled.courseid==course_id.id ).first() is None:

		course1 = DBSession.query(Course).filter_by(access_code=access_code).first()
		DBSession.add(Enrolled(userid=currentuser.id, courseid=course1.id))
		message = "You have successfully added "  + course1.name
		student_courses = DBSession.query(Course,Enrolled,User).filter(Course.id==Enrolled.courseid).filter(Enrolled.userid==currentuser.id).filter(Course.id==User.id).all()
		if len(student_courses) == 1:
  		    return HTTPFound(location = request.route_url('home'))
	    else:
		message = "You are already enrolled in the Course"

    owner_courses = []
    enrolled_courses = []
    if group["is_teacher"]:
        owner_courses = Course.owner_courses(request.authenticated_userid)
    elif group["is_student"]:
        enrolled_courses = Enrolled.enrolled_courses(request.authenticated_userid)

    return {"layout": logged_layout(),
            "logged_in" : request.authenticated_userid,
            "custom_scripts" : custom_scripts,
	    "message" : message,
            "owner_courses" : owner_courses,
            "enrolled_courses" : enrolled_courses,
	    "student_courses" : student_courses,
	    "is_admin" : group["is_admin"], "is_teacher" : group["is_teacher"], "is_student" : group["is_student"],
	    "page_title" : "Signup to a Course"           }
