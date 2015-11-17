from pyramid.view import (view_config, forbidden_view_config)
from pyramid.renderers import get_renderer
from pyramid.response import FileResponse, Response
from pyramid.request import Request
from pyramid.httpexceptions import (HTTPFound, HTTPNotFound)
import os.path

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


@view_config(route_name='reaction_image', renderer='ltefserver:templates/new/reaction_image.pt', permission='study')
def learning_reaction_image_view(request):

    # retrieve basename
    basename = request.matchdict["basename"]

    reaction = cat.get_reaction_by_basename(basename)

    # Initialize draw SVGRenderer object
    svg_reanderer = draw.SVGRenderer()

    svg_data = ""
    svg_data = svg_reanderer.renderReactionToBuffer(reaction.getInstance(), layout=False)

    svg_data = update_svg_size(svg_data, '100%', '-1')

    return {"svg_data" : svg_data
            }



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

    # retrieve basename
    basename = request.matchdict["basename"]
    # Get the reaction that will be genereated
    reaction = cat.get_reaction_by_basename(basename)

    random_file_id = str(uuid.uuid4())[0:10].upper()  # or whatever
    # needs to be random file name
    filename = "svg_data_" + random_file_id

    # Add any custom scripts
    custom_scripts = []
    custom_scripts.append('/bootstrap/js/learning_reactions.js')

    # Get the  current user's security privileges
    group = group_security(request.authenticated_userid)

    owner_courses = []
    enrolled_courses = []
    if group["is_teacher"]:
        owner_courses = Course.owner_courses(request.authenticated_userid)
    elif group["is_student"]:
        enrolled_courses = Enrolled.enrolled_courses(request.authenticated_userid)

    # Initialize draw SVGRenderer object
    svg_reanderer = draw.SVGRenderer()

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

    svg_data = ""
    svg_data = svg_reanderer.renderReactionToBuffer(reaction, layout=False)
    svg_data = svg_reanderer.renderReactionToBuffer(reaction, layout=False)
    svg_data = update_svg_size(svg_data, '100%', '-1')

    return {"layout" : logged_layout(),
            "basename" : basename,
	        "custom_scripts" : custom_scripts,
            "is_admin" : group["is_admin"], "is_teacher" : group["is_teacher"], "is_student" : group["is_student"],
            "reaction_description" : reaction.desc,
            "page_title" : reaction.full_name,
	        "rgroups" : reaction.rgroups,
            "logged_in" : request.authenticated_userid,
            "link_to_gen_picture" : link_to_gen_picture,
            "svg_data" : svg_data,
            "owner_courses" : owner_courses,
            "enrolled_courses" : enrolled_courses,
            "filename" : filename,
}



@view_config(route_name='learn_by_example_reaction', renderer='ltefserver:templates/new/learn_by_example_reaction.pt', permission='study')
def learn_by_example_reaction_view(request):

    basename = request.matchdict["basename"]
    chapter_name = request.matchdict["chapter"]
    reaction_name = request.matchdict["reaction"]
    custom_scripts = []
    message = ""
    reaction_description = ""
    currentuser = DBSession.query(User).filter(User.username == request.authenticated_userid).first()
    group = group_security(request.authenticated_userid)
    owner_courses = []
    enrolled_courses = []

    random_file_id = str(uuid.uuid4())[0:10].upper()  # or whatever
    # needs to be random file name
    filename = "svg_data_" + random_file_id

    if group["is_teacher"]:
        owner_courses = Course.owner_courses(request.authenticated_userid)
        current_chapter = DBSession.query(Chapter).filter(Course.owner == currentuser.id).filter(Chapter.course == Course.id ).filter(Course.name == basename).filter(Chapter.title == chapter_name).first()
    elif group["is_student"]:
        enrolled_courses = Enrolled.enrolled_courses(request.authenticated_userid)
        current_chapter = DBSession.query(Chapter).filter(Enrolled.userid == currentuser.id).filter(Chapter.course == Course.id).filter(Course.name == basename).filter(Enrolled.courseid == Course.id).filter(Chapter.title == chapter_name ).first()

    custom_scripts.append('/bootstrap/js/learning_reactions.js')
    reaction = cat.get_reaction_by_basename(reaction_name)

    # Initialize draw SVGRenderer object
    svg_reanderer = draw.SVGRenderer()

    reac = DBSession.query(Reac).filter(Reac.basename == reaction_name).first()
    customizable_reaction = DBSession.query(Customizable_reaction).filter(Customizable_reaction.reaction == reac.id).filter(Customizable_reaction.chapter == current_chapter.id).first()

    #If there is a customizable reaction name or description display it
    if len(customizable_reaction.description) > 0:
        reaction_description = customizable_reaction.description
    else:
        reaction_description = reaction.desc

    if len(customizable_reaction.title) > 0:
        reaction_title = customizable_reaction.title
    else:
        reaction_title = reaction.full_name

    #if len(customizable_reaction.description) > 0:
    #    reaction_description = reaction.desc
    #else:
    #    reaction_description = customizable_reaction.description

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

    static_svg_path = 'ltefserver/static/reaction_images/'
    static_svg_image = "false"
    svg_other = 'not working'
    svg_data = ""
    if os.path.isfile(static_svg_path + reaction_name + '.svg'):
        file_svg_reaction = open(static_svg_path + reaction_name + '.svg', 'r')
        svg_image = file_svg_reaction.read()
        if len(svg_image) != 0:
            svg_other = svg_image
        else:
            svg_other = "Error reaction image empty"

        static_svg_image = "true"
    else:
        svg_data = ""
        svg_data = svg_reanderer.renderReactionToBuffer(reaction, layout=False)
        svg_data = svg_reanderer.renderReactionToBuffer(reaction, layout=False) # hack because the other image wouldn't be displayed correctly
        svg_data = update_svg_size(svg_data, '100%', '-1')
        static_svg_image = "false"

    return {"layout": logged_layout(),
            "logged_in" : request.authenticated_userid,
            "message" : message,
            "custom_scripts" : custom_scripts,
            "is_admin" : group["is_admin"], "is_teacher" : group["is_teacher"], "is_student" : group["is_student"],
            "page_title" : reaction_title,
	        "rgroups" : reaction.rgroups,
	        "link_to_gen_picture" : link_to_gen_picture,
            "svg_data" : svg_data,
            "svg_other" : svg_other,
            "owner_courses" : owner_courses,
            "enrolled_courses" : enrolled_courses,
    	    "reaction_description" : reaction_description,
	        "reaction" : reaction_name,
            "filename" : filename,
            "basename" : reaction_name,
            "static_svg_image" : static_svg_image,
    }


def update_svg_size(svg, width, height):

    updated_svg = ""

    # Chop off the xml tag
    svg = svg[svg.find('\n') + 1:]
    # Modify height and width of the svg tag
    svgline = svg[:svg.find('\n')]

    if height != '-1':
        svglineparts = re.split('height=".*?"', svgline)
        svgline = svglineparts[0] + 'height="' + height + '"' + svglineparts[1]

    if width != '-1':
        svglineparts = re.split('width=".*?"', svgline)
        svgline = svglineparts[0] + 'width="' +  width +   '"' + svglineparts[1]

    updated_svg = svgline + "\n" + svg[svg.find('\n') + 1 :]

    return updated_svg
