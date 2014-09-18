from pyramid.view import (view_config, forbidden_view_config)
from pyramid.renderers import get_renderer
from pyramid.response import FileResponse, Response
from pyramid.request import Request
from pyramid.httpexceptions import (HTTPFound, HTTPNotFound)

from sqlalchemy.exc import DBAPIError
from .models import (
    DBSession,
    MyModel,
    )

from pyramid.security import (
    remember,
    forget,
    )

from .security import USERS

import os
import sys
import random
import uuid
import base64
import datetime
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
quiz_problems = {}


def site_layout():
    renderer = get_renderer("templates/layout.pt")
    layout = renderer.implementation().macros['layout']
    return layout


@view_config(route_name='home', renderer='templates/home.pt', permission='view')
def home_view(request):
    #print "Home view fired up, authenticated_userid is " + str(request.authenticated_userid)
    return {"layout" : site_layout(), 
            "base_to_full" : cat.base_to_full, 
            "logged_in" : request.authenticated_userid }


@view_config(route_name='learning', renderer='templates/learning.pt', permission='view')
def learning_view(request):
    return {"layout" : site_layout(), 
            "base_to_full" : cat.base_to_full, 
            "logged_in" : request.authenticated_userid }


@view_config(route_name='learning_reaction', renderer='templates/learning_reaction.pt', permission='view')
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

    return {"layout" : site_layout(),
            "basename" : basename, 
            "full_name" : reaction.full_name, 
            "reaction_description" : reaction.desc, 
            "rgroups" : reaction.rgroups, 
            "logged_in" : request.authenticated_userid }


@view_config(route_name='img', permission='view')
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


@view_config(route_name='img_by_id', permission='view')
def img_by_id_view(request):

    problem_id = request.matchdict["id"]
    which = request.matchdict["which"]

    response = None

    if problem_id in quiz_problems.keys():
        if which == "reaction":
            response = Response(content_type='image/png', body=quiz_problems[problem_id][0])
        elif which.isdigit():
            response = Response(content_type='image/png', body=quiz_problems[problem_id][1][int(which)][0])
        else:
            response = HTTPNotFound()
    else:
        response = HTTPNotFound()

    return response



@view_config(route_name='quiz_reactants', renderer='templates/quiz_reactants.pt', permission='view')
def quiz_reactants_view(request):
    global quiz_problems
    session = request.session

    mode = request.matchdict["basename"]
    problem_id = ""
    basename = ""
    full_name = ""
    message = ""
    result = False
    state = "ask"


    # Generate a problem, store the objects, present to user
    if 'quiz_type' not in session or session['quiz_type'] != 'reactants' or session['problem_id'] not in quiz_problems.keys():
        session.invalidate()
        problem_id = str(uuid.uuid4())
        session['quiz_type'] = 'reactants'
        session['problem_id'] = problem_id
        state = "ask"
        
        # select a reaction randomly
        if mode == "random":
            basename = random.choice(cat.get_sorted_basenames())
        else:
            basename = mode
        reaction = cat.get_reaction_by_basename(basename)
        full_name = reaction.full_name

        # prepare instance, cut off reactants
        instance = reaction.getInstance()
        fullImage = draw.renderReactionToBuffer(instance).tostring()

        reactants = instance.reactants

        molecule = chem.Molecule()
        molecule.addAtom(chem.Atom("?", 0, 0, 0, 0, 0))

        instance.reactants = [molecule]

        # Reaction image without reactants
        mainImage = draw.renderReactionToBuffer(instance).tostring()

        reactantImages = []
        for mol in reactants:
            image = draw.renderMoleculeToBuffer(mol).tostring()
            reactantImages.append([image, True])    # indicate that these are correct answers


        # Generate wrong answers here, add to reactantImages
        for mol in chem.mutateMolecules(reactants):
            image = draw.renderMoleculeToBuffer(mol).tostring()
            reactantImages.append([image, False])    # indicate that these are wrong answers

        random.shuffle(reactantImages)

        quiz_problems[problem_id] = [mainImage, reactantImages, fullImage]

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
            for index in range(0, len(quiz_problems[problem_id][1])):
                val = quiz_problems[problem_id][1][index][1]
                if val:
                    correctAnswers.append(str(index))
            #print "Correct answer is " + str(set(correctAnswers))

            if set(ans) != set(correctAnswers):
                message = "Wrong!"
                result = False
                #print "Your set: " + str(set(ans))
                #print "Good set: " + str(set(correctAnswers))
            else:
                message = "Correct! You selected what's necessary and nothing else."
                result = True

            # Once user has made a choice, replace cut reaction with a full one
            quiz_problems[problem_id][0] = quiz_problems[problem_id][2]

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
            "indeces" : range(0, len(quiz_problems[problem_id][1])),
            "style_t" : style_t,
            "message" : message,
            "result" : result,
            "state" : state,
            "logged_in" : request.authenticated_userid 
        }


@view_config(route_name='quiz_products', renderer='templates/quiz_products.pt', permission='view')
def quiz_products_view(request):
    global quiz_problems
    session = request.session

    mode = request.matchdict["basename"]
    #print "Mode: " + mode
    problem_id = ""
    basename = ""
    full_name = ""
    message = ""
    result = False
    state = "ask"


    # Generate a problem, store the objects, present to user
    if 'quiz_type' not in session or session['quiz_type'] != 'products' or session['problem_id'] not in quiz_problems.keys():
        session.invalidate()
        problem_id = str(uuid.uuid4())
        session['quiz_type'] = 'products'
        session['problem_id'] = problem_id
        state = "ask"
        
        # select a reaction randomly
        if mode == "random":
            basename = random.choice(cat.get_sorted_basenames())
        else:
            basename = mode
        reaction = cat.get_reaction_by_basename(basename)
        full_name = reaction.full_name

        # prepare instance, cut off products
        instance = reaction.getInstance()
        fullImage = draw.renderReactionToBuffer(instance).tostring()

        products = instance.products

        molecule = chem.Molecule()
        molecule.addAtom(chem.Atom("?", 0, 0, 0, 0, 0))

        instance.products = [molecule]

        # Reaction image without products
        mainImage = draw.renderReactionToBuffer(instance).tostring()

        reactantImages = []
        for mol in products:
            image = draw.renderMoleculeToBuffer(mol).tostring()
            reactantImages.append([image, True])    # indicate that these are correct answers


        # Generate wrong answers here, add to reactantImages
        for mol in chem.mutateMolecules(products):
            image = draw.renderMoleculeToBuffer(mol).tostring()
            reactantImages.append([image, False])    # indicate that these are wrong answers

        random.shuffle(reactantImages)

        quiz_problems[problem_id] = [mainImage, reactantImages, fullImage]

        session['basename'] = basename
        print "Started a quiz (products) session for " + basename + ", id = " + problem_id

    # Depending on request parameters, either
    #   - continue session, or
    #   - present the answer to problem and a show a button to get a new problem
    else:
        problem_id = session['problem_id']
        basename = session['basename']
        quiz_type = session['quiz_type']
        print "Resuming a quiz (products) session for " + basename + ", id = " + problem_id
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
            for index in range(0, len(quiz_problems[problem_id][1])):
                val = quiz_problems[problem_id][1][index][1]
                if val:
                    correctAnswers.append(str(index))
            #print "Correct answer is " + str(set(correctAnswers))

            if set(ans) != set(correctAnswers):
                message = "Wrong!"
                result = False
                #print "Your set: " + str(set(ans))
                #print "Good set: " + str(set(correctAnswers))
            else:
                message = "Correct! You selected what's necessary and nothing else."
                result = True

            # Once user has made a choice, replace cut reaction with a full one
            
            quiz_problems[problem_id][0] = quiz_problems[problem_id][2]

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
            "indeces" : range(0, len(quiz_problems[problem_id][1])),
            "style_t" : style_t,
            "message" : message,
            "result" : result,
            "state" : state,
            "logged_in" : request.authenticated_userid 
        }


@view_config(route_name='quiz_reaction', renderer='templates/quiz_reaction.pt', permission='view')
def quiz_reaction_view(request):
    global quiz_problems
    session = request.session

    problem_id = ""
    basename = ""
    full_name = ""
    message = ""
    result = False
    state = "ask"


    # Generate a problem, store the objects, present to user
    if 'quiz_type' not in session or session['quiz_type'] != 'reaction' or session['problem_id'] not in quiz_problems.keys():
        session.invalidate()
        problem_id = str(uuid.uuid4())
        session['quiz_type'] = 'reaction'
        session['problem_id'] = problem_id
        state = "ask"
        
        # select a reaction randomly
        basename = random.choice(cat.get_sorted_basenames())
        reaction = cat.get_reaction_by_basename(basename)
        full_name = reaction.full_name

        # prepare instance, cut off products
        instance = reaction.getInstance()
        mainImage = draw.renderReactionToBuffer(instance).tostring()

        # Generate wrong answers here, add to reactantImages
        #
        #


        quiz_problems[problem_id] = (mainImage, basename, full_name)

        session['basename'] = "unknown"
        print "Started a quiz (reaction) session for " + basename + ", id = " + problem_id

    # Depending on request parameters, either
    #   - continue session, or
    #   - present the answer to problem and a show a button to get a new problem
    else:
        problem_id = session['problem_id']
        print "Resuming a quiz (reaction) session for " + problem_id

        if "choice" in request.GET:

            print "Literally: " + str(request.GET)
            ans = request.GET["choice"]
            print "Answer given is " + str(ans)

            # Invalidate the session
            state = "tell"
            session.invalidate()

            # Check if given answer is correct
            correctAnswer = quiz_problems[problem_id][1]

            print "Correct answer is " + correctAnswer

            if correctAnswer != ans:
                message = "Wrong! This is actually " + quiz_problems[problem_id][2]
                result = False
                #print "Your set: " + str(set(ans))
                #print "Good set: " + str(set(correctAnswers))
            else:
                message = "Correct! This indeed is " + quiz_problems[problem_id][2]
                result = True

    return {
            "layout": site_layout(),
            "basename" : "unknown_reaction",
            "full_name" : "Unknown Reaction",
            "problem_id" : problem_id,
            "message" : message,
            "result" : result,
            "state" : state,
            "base_to_full" : cat.base_to_full,
            "logged_in" : request.authenticated_userid 
        }


@view_config(route_name='synthesis', renderer='templates/synthesis.pt', permission='view')
def synthesis_view(request):
    return {"layout": site_layout(),
            "logged_in" : request.authenticated_userid }

@view_config(route_name='addreaction', renderer='templates/addreaction.pt', permission='view')
def addreaction_view(request):
    return {"layout": site_layout(),
            "logged_in" : request.authenticated_userid }


@view_config(route_name='about', renderer='templates/about.pt', permission='view')
def about_view(request):
    return {"layout": site_layout(),
            "logged_in" : request.authenticated_userid }


@view_config(route_name='contact', renderer='templates/contact.pt', permission='view')
def contact_view(request):
    state = "new form"
    if "txtComment" in request.POST:
        #print request.POST["txtComment"]
        state = "sent"        
        with open("contact.txt", "a") as myfile:
            myfile.write(str(datetime.datetime.now()) + "\n")
            myfile.write("-------MESSAGE--------\n")
            myfile.write(request.POST["txtComment"] + "\n")
            myfile.write("----END OF MESSAGE----\n\n")


    return {"layout": site_layout(), 
            "state" : state,
            "logged_in" : request.authenticated_userid }


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




@view_config(route_name='login', renderer='templates/login.pt')
@forbidden_view_config(renderer='templates/login.pt')
def login(request):
    #print "Login view fired up, authenticated_userid is " + str(request.authenticated_userid)

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
        if USERS.get(login) == password:
            headers = remember(request, login)
            #print "Authentication worked, returning HTTPFound with location " + came_from
            #print "Headers are " + str(headers)
            return HTTPFound(location = came_from,
                             headers = headers)
        message = 'Failed login'

    return dict(
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