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





@view_config(route_name='learning', renderer='ltefserver:templates/new/learning.pt', permission='study')
def learning_view(request):
    custom_scripts = []

    group = group_security(request.authenticated_userid)

    owner_courses = []
    enrolled_courses = []
    if group["is_teacher"]:
        owner_courses = Course.owner_courses(request.authenticated_userid)
    elif group["is_student"]:
        enrolled_courses = Enrolled.enrolled_courses(request.authenticated_userid)


    return {"layout" : logged_layout(),
            "base_to_full" : cat.base_to_full,
            "custom_scripts" : custom_scripts,
	        "logged_in" : request.authenticated_userid,
	        "is_admin" : group["is_admin"], "is_teacher" : group["is_teacher"], "is_student" : group["is_student"],
	        "page_title" : "Learn By Example",
            "owner_courses" : owner_courses,
            "enrolled_courses" : enrolled_courses }


@view_config(route_name='learning_reaction', renderer='ltefserver:templates/new/learning_reaction.pt', permission='study')
def learning_reaction_view(request):
    custom_scripts = []
    # Sessions experiment; ignore
    # session = request.session
    # if 'abc' in session:
    #     session['fred'] = 'yes'
    # session['abc'] = '123'
    # if 'fred' in session:
    #     print 'Fred was in the session'
    # else:
    #     print 'Fred was not in the session'
    # End of session experiment
    custom_scripts = []
    custom_scripts.append('/bootstrap/js/learning_reactions.js')
    basename = request.matchdict["basename"]
    reaction = cat.get_reaction_by_basename(basename)
    group = group_security(request.authenticated_userid)

    # A hack for Sharonna
    # Display an external image in place of the generic reaction image (if there is one)
    link_to_gen_picture = None
    static_image_filename = basename + '.png'
    static_image_path = 'ltefserver/static/reaction_images'

    if os.path.isfile(os.path.join(static_image_path, static_image_filename)) :
        link_to_gen_picture = request.static_url('ltefserver:static/reaction_images/' + static_image_filename)
    else:
        link_to_gen_picture = request.route_url('home') + 'img/' + basename + '/generic/image.png'
    # End of the hack

    svg_data = draw.renderReactionToBuffer(reaction, render_format="svg", layout=False).tostring()

    # Chop off the xml tag
    svg_data = svg_data[svg_data.find('\n') + 1:]
    # Modify height and width of the svg tag
    svgline = svg_data[:svg_data.find('\n')]
    svglineparts = re.split('width=".*?" height=".*?"', svgline)
    svgline = svglineparts[0] + 'width="90%"' + svglineparts[1]
    svg_data = svgline + "\n" + svg_data[svg_data.find('\n') + 1 :]

    owner_courses = []
    enrolled_courses = []
    if group["is_teacher"]:
        owner_courses = Course.owner_courses(request.authenticated_userid)
    elif group["is_student"]:
        enrolled_courses = Enrolled.enrolled_courses(request.authenticated_userid)

    return {"layout" : logged_layout(),
            "basename" : basename,
	    "custom_scripts" : custom_scripts,
            "is_admin" : group["is_admin"], "is_teacher" : group["is_teacher"], "is_student" : group["is_student"],
            "full_name" : reaction.full_name,
            "reaction_description" : reaction.desc,
            "page_title" : reaction.full_name,
	    "rgroups" : reaction.rgroups,
            "logged_in" : request.authenticated_userid,
            "link_to_gen_picture" : link_to_gen_picture,
            "svg_data" : svg_data,
            "owner_courses" : owner_courses,
            "enrolled_courses" : enrolled_courses,
}



@view_config(route_name='learn_by_example_reaction', renderer='ltefserver:templates/new/learn_by_example_reaction.pt', permission='study')
def learn_by_example_reaction_view(request):

    basename = request.matchdict["basename"]
    chapter_name = request.matchdict["chapter"]
    reaction_name = request.matchdict["reaction"]
    custom_scripts = []
    message = ""
    currentuser = DBSession.query(User).filter(User.username == request.authenticated_userid).first()
    group = group_security(request.authenticated_userid)

    custom_scripts.append('/bootstrap/js/learning_reactions.js')
    reaction = cat.get_reaction_by_basename(reaction_name)

    # A hack for Sharonna
    # Display an external image in place of the generic reaction image (if there is one)
    link_to_gen_picture = None
    static_image_filename = reaction_name + '.png'
    static_image_path = 'ltefserver/static/reaction_images'

    if os.path.isfile(os.path.join(static_image_path, static_image_filename)) :
        link_to_gen_picture = request.static_url('ltefserver:static/reaction_images/' + static_image_filename)
    else:
        link_to_gen_picture = request.route_url('home') + 'img/' + reaction_name + '/generic/image.png'
    # End of the hack

    svg_data = draw.renderReactionToBuffer(reaction, render_format="svg",  layout=False).tostring()

    # Chop off the xml tag
    svg_data = svg_data[svg_data.find('\n') + 1:]
    # Modify height and width of the svg tag
    svgline = svg_data[:svg_data.find('\n')]
    svglineparts = re.split('width=".*?" height=".*?"', svgline)
    svgline = svglineparts[0] + 'width="90%"' + svglineparts[1]
    svg_data = svgline + "\n" + svg_data[svg_data.find('\n') + 1 :]

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
            "page_title" : reaction.full_name,
	        "rgroups" : reaction.rgroups,
	        "link_to_gen_picture" : link_to_gen_picture,
            "svg_data" : svg_data,
            "owner_courses" : owner_courses,
            "enrolled_courses" : enrolled_courses,
    	    "reaction_description" : reaction.desc,
	        "reaction" : reaction_name
    }
