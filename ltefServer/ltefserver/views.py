from pyramid.view import view_config
from pyramid.renderers import get_renderer
from pyramid.response import FileResponse, Response
from pyramid.request import Request
from pyramid.httpexceptions import HTTPNotFound

from sqlalchemy.exc import DBAPIError
from .models import (
    DBSession,
    MyModel,
    )

import os
import sys
import random
import uuid
import base64
sys.path.append('../python')
sys.path.append('./indigo-python-1.1.12')
import rxn
import chem
import draw
import catalog

# Create a catalog object upon loading this module
# Let's not use 'global' keyword in functions since we should not be
# modifying this anyway.
cat = catalog.Catalog()

# Experiment
# A dictionary from a unique identifying string (timestamp?) to an object
# containing the reaction image without reactants, and a set of possible answer images,
# complete with boolean flags to indicate whether they are right or wrong
quiz_reactants_problems = {}


def site_layout():
    renderer = get_renderer("templates/layout.pt")
    layout = renderer.implementation().macros['layout']
    return layout


@view_config(route_name='home', renderer='templates/index.pt')
def home_view(request):
    return {'project': 'MyProject'}


@view_config(route_name='tools', renderer='templates/tools.pt')
def tools_view(request):
    return {"layout": site_layout()}


@view_config(route_name='learning', renderer='templates/learning.pt')
def learning_view(request):
    return {"layout" : site_layout(), "base_to_full" : cat.base_to_full}


@view_config(route_name='learning_reaction', renderer='templates/learning_reaction.pt')
def learning_reaction_view(request):
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


    basename = request.matchdict["basename"]
    reaction = cat.get_reaction_by_basename(basename)

    return {"layout" : site_layout(), "basename" : basename, "full_name" : reaction.full_name, "reaction_description" : reaction.desc, "rgroups" : reaction.rgroups}


@view_config(route_name='img')
def img_view(request):

    param_str = request.matchdict["filename"]
    mode = request.matchdict["what"]
    basename = request.matchdict["basename"]

    reaction = cat.get_reaction_by_basename(basename)

    response = None

    # Renders a generic reaction from catalog
    if mode == "generic":
        response = Response(content_type='image/png', body=draw.renderReactionToBuffer(reaction).tostring())

    # Renders an instance generated from generic using parameters
    elif mode == "instance":
        instance = reaction.getInstance()
        response = Response(content_type='image/png', body=draw.renderReactionToBuffer(instance).tostring())
    
    # Renders a generic r-group molecule using params
    elif mode == "rgroup":
        params = param_str.split(",")
        # first arg is "R1", "R2", etc.
        # second arg is the list index of specific molecule which the group could be
        # e.g. "...?R1,0" is for the first choice of R1
        if len(params) == 2:
            buf = draw.renderRGroupToBuffer(reaction, params[0].upper(), int(params[1]))
            if buf is not None:
                response = Response(content_type='image/png', body=buf.tostring())
    
    # Renders an instance without reactants
    elif mode == "noreactants":
        instance = reaction.getInstance()
        instance.reactants = []
        response = Response(content_type='image/png', body=draw.renderReactionToBuffer(instance).tostring())

    # Bad URL
    else:
        response = HTTPNotFound()

    return response


@view_config(route_name='img_by_id')
def img_by_id_view(request):

    problem_id = request.matchdict["id"]
    which = request.matchdict["which"]

    response = None

    if problem_id in quiz_reactants_problems.keys():
        if which == "reaction":
            response = Response(content_type='image/png', body=quiz_reactants_problems[problem_id][0])
        elif which.isdigit():
            response = Response(content_type='image/png', body=quiz_reactants_problems[problem_id][1][int(which)][0])
        else:
            response = HTTPNotFound()
    else:
        response = HTTPNotFound()

    return response


@view_config(route_name='quiz_random')
def quiz_random_view(request):
    subreq = Request.blank(random.choice(['/tools/quiz/reactants', '/tools/quiz/products', '/tools/quiz/reaction']))
    return request.invoke_subrequest(subreq)


@view_config(route_name='quiz_reactants', renderer='templates/quiz_reactants.pt')
def quiz_reactants_view(request):
    session = request.session

    problem_id = ""
    basename = ""
    full_name = ""
    message = ""
    result = False
    state = "ask"


    # Generate a problem, store the objects, present to user
    if 'quiz_type' not in session or session['problem_id'] not in quiz_reactants_problems.keys():
        session.invalidate()
        problem_id = str(uuid.uuid4())
        session['quiz_type'] = 'reactants'
        session['problem_id'] = problem_id
        state = "ask"
        
        # select a reaction randomly
        basename = random.choice(cat.get_sorted_basenames())
        reaction = cat.get_reaction_by_basename(basename)
        full_name = reaction.full_name

        # prepare instance, cut off reactants
        instance = reaction.getInstance()
        fullImage = draw.renderReactionToBuffer(instance).tostring()

        reactants = instance.reactants
        instance.reactants = []

        # Reaction image without reactants
        mainImage = draw.renderReactionToBuffer(instance).tostring()

        reactantImages = []
        for mol in reactants:
            image = draw.renderMoleculeToBuffer(mol).tostring()
            reactantImages.append([image, True])    # indicate that these are correct answers


        # Generate wrong answers here, add to reactantImages
        #
        #

        random.shuffle(reactantImages)

        global quiz_reactants_problems
        quiz_reactants_problems[problem_id] = [mainImage, reactantImages, fullImage]

        session['basename'] = basename
        print "Started a quiz (reactants) session for " + basename + ", id = " + problem_id

    # Depending on request parameters, either
    #   - continue session, or
    #   - present the answer to problem and a show a button to get a new problem
    else:
        problem_id = session['problem_id']
        basename = session['basename']
        quiz_type = session['quiz_type']
        print "Resuming a quiz (reactants) session for " + basename + ", id = " + problem_id
        reaction = cat.get_reaction_by_basename(basename)
        full_name = reaction.full_name

        if "answer" in request.GET:

            #print "Literally: " + str(request.GET)
            ans = request.GET["answer"].split(",")
            #print "Answer given is " + str(ans)

            # Invalidate the session
            state = "tell"
            session.invalidate()

            # Check if given answer is correct
            correctAnswers = []
            for index in range(0, len(quiz_reactants_problems[problem_id][1])):
                val = quiz_reactants_problems[problem_id][1][index][1]
                if val:
                    correctAnswers.append(str(index))
            #print "Correct answer is " + str(set(correctAnswers))

            if set(ans) != set(correctAnswers):
                message = "Wrong!"
                result = False
                #print "Your set: " + str(set(ans))
                #print "Good set: " + str(set(correctAnswers))
            else:
                message = "Correct!"
                result = True

            # Once user has made a choice, replace cut reaction with a full one
            global quiz_reactants_problems
            quiz_reactants_problems[problem_id][0] = quiz_reactants_problems[problem_id][2]

    # prepare styles
    style_t = (
            "background-image: url('" + request.route_url("home") + "img/q_" + problem_id + "/",
            ".png');"
        )

     
    return {
            "layout": site_layout(),
            "basename" : basename,
            "full_name" : full_name,
            "problem_id" : problem_id,
            "indeces" : range(0, len(quiz_reactants_problems[problem_id][1])),
            "style_t" : style_t,
            "message" : message,
            "result" : result,
            "state" : state,
        }


@view_config(route_name='quiz_products', renderer='templates/quiz_products.pt')
def quiz_products_view(request):
    return {"layout": site_layout()}


@view_config(route_name='quiz_reaction', renderer='templates/quiz_reaction.pt')
def quiz_reaction_view(request):
    return {"layout": site_layout()}


@view_config(route_name='synthesis', renderer='templates/synthesis.pt')
def synthesis_view(request):
    return {"layout": site_layout()}



# def my_view(request):
#     try:
#         one = DBSession.query(MyModel).filter(MyModel.name == 'one').first()
#     except DBAPIError:
#         return Response(conn_err_msg, content_type='text/plain', status_int=500)
#     return {'one': one, 'project': 'dbtutorial'}

# conn_err_msg = """\
# Pyramid is having a problem using your SQL database.  The problem
# might be caused by one of the following things:

# 1.  You may need to run the "initialize_dbtutorial_db" script
#     to initialize your database tables.  Check your virtual 
#     environment's "bin" directory for this script and try to run it.

# 2.  Your database server may not be running.  Check that the
#     database server referred to by the "sqlalchemy.url" setting in
#     your "development.ini" file is running.

# After you fix the problem, please restart the Pyramid application to
# try it again.
# """