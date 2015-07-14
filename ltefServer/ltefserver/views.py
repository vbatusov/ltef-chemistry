from pyramid.view import (view_config, forbidden_view_config)
from pyramid.renderers import get_renderer
from pyramid.response import FileResponse, Response
from pyramid.request import Request
from pyramid.httpexceptions import (HTTPFound, HTTPNotFound)


from sqlalchemy.exc import DBAPIError
from .models import (
    DBSession,
    Group,
    User,
    Reac,
    List,
    Course,
    Enrolled,
    )

from pyramid.security import (
    remember,
    forget,
    )

from .security import checkCredentials, getHash

import os
import sys
import random
import uuid
import bcrypt
#import base64
import datetime
sys.path.append('../python')
sys.path.append('./indigo-python')
import rxn
import chem
import draw
import catalog
import copy




# Create a catalog object upon loading this module
# Let's not use 'global' keyword in functions since we should not be
# modifying this anyway.
cat = catalog.Catalog()

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
    renderer = get_renderer("templates/main_layout.pt")
    layout = renderer.implementation().macros['main_layout']
    return layout

def site_layout():
    renderer = get_renderer("templates/layout.pt")
    layout = renderer.implementation().macros['layout']
    return layout

def logged_layout():
    renderer = get_renderer("templates/logged_layout.pt")
    layout = renderer.implementation().macros['logged_layout']
    return layout



@view_config(route_name='manageusers', renderer='templates/new/manageusers.pt', permission='dominate')
def manageusers_view(request):

    message = ""
    
    custom_scripts = []
    custom_scripts.append("/bootstrap/js/manageusers.js")
    if 'addform.submitted' in request.params:
        # TODO: add checks for valid input
        u = request.params['username']
	firstname = request.params['first_name']
	lastname = request.params['last_name']
	id = request.params['id_number']
	email = request.params['email']
        g = request.params['group']
        p = request.params['password']
	password_confirm = request.params['confirm_password']
	
	if p == password_confirm:
             if DBSession.query(User).filter_by(username=u).first() is None:
                DBSession.add(User(username=u, group=g,firstname=firstname, lastname=lastname, studentNumber=id, email=email, phash=getHash(p)))
                message = "User '" + u + "' has been added"
             else:
                message = "User '" + u + "' already exists"

                #return HTTPFound(location = request.route_url('manageusers'))
	else:
	     message = "Passwords do not match"
	

    elif 'editform.username' in request.params:
        u = request.params['editform.username']
        # apply changes
        if request.params['editOption'] == 'password':
            DBSession.query(User).filter(User.username == u).update({"phash": getHash(request.params['password'])})
            message = "Password changed for user '" + u + "'"

        elif request.params['editOption'] == 'group':
            if not u == User.ADMIN and not u == User.GUEST:
                DBSession.query(User).filter(User.username == u).update({"group": request.params['group']})
                message = "User '" + u + "' has been reassigned to another group"
            else:
                message = "User '" + u + "' cannot be reassigned to another group"

        elif request.params['editOption'] == 'erase':
            # NOTE: update this logic as user data spreads through database
            if not u == User.ADMIN and not u == User.GUEST:
                DBSession.query(User).filter(User.username == u).delete()
                message = "User '" + u + "' has been permanently erased"
            else:
                message = "User '" + u + "' cannot be erased"

        #return HTTPFound(location = request.route_url('manageusers'))

    admins = DBSession.query(User,Group).filter(User.group==Group.id).filter(Group.desc==Group.ADMIN).all()
    teachers = DBSession.query(User,Group).filter(User.group==Group.id).filter(Group.desc==Group.TEACHER).all()
    students = DBSession.query(User,Group).filter(User.group==Group.id).filter(Group.desc==Group.STUDENT).all()
    guests = DBSession.query(User,Group).filter(User.group==Group.id).filter(Group.desc==Group.GUEST).all()

    groups = DBSession.query(Group).all()

    return {"layout" : logged_layout(), 
            "logged_in" : request.authenticated_userid,
            "admins" :  admins, "teachers" : teachers, "students" : students, "guests" : guests,
            "groups" : groups,
  	    "custom_scripts" : custom_scripts,
            "message" : message,
	    "page_title" : "Manage Users"
            }

@view_config(route_name='managelists', renderer='templates/new/managelists.pt', permission='educate')
def managelists_view(request):
    message = ""

    user = DBSession.query(User).filter(User.username == request.authenticated_userid).first()

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

    return {"layout" : logged_layout(), 
            "custom_scripts" : custom_scripts,
	    "logged_in" : request.authenticated_userid,
            "lists" : lists,
            "message" : message,
	    "page_title" : "Manage Reaction Lists"
            }

@view_config(route_name='editlist', renderer='templates/editlist.pt', permission='educate')
def editlist_view(request):

    message = ""

    title = ""
    desc = ""
    new = True
    # Data for select boxes: lists of pairs (full reaction name, reaction id)
    leftbox = []
    rightbox = []

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

    return {"layout" : site_layout(), 
            "logged_in" : request.authenticated_userid,            
            "message" : message,
            "title" : title,
            "desc" : desc,
            "leftbox" : leftbox,
            "rightbox" : rightbox,
            "new" : new,
            }          


@view_config(route_name='home', renderer='templates/new/home.pt', permission='study')
def home_view(request):
    #print "Home view fired up, authenticated_userid is " + str(request.authenticated_userid)

    custom_scripts = []

    is_guest = Group.GUEST
    is_admin = None
    is_teacher = None
    is_student = None
    currentuser = DBSession.query(User).filter(User.username == request.authenticated_userid).first()
    teacher_courses = DBSession.query(Course).filter(Course.owner == currentuser.id).all() 
    student_courses = DBSession.query(Course,Enrolled).filter(Course.id==Enrolled.courseid).filter(Enrolled.userid==currentuser.id).all() 
    user = DBSession.query(User).filter_by(username=request.authenticated_userid).first()
    if user is not None:
        group = DBSession.query(Group).filter_by(id=user.group).first()
        if group is not None:
            is_admin = (group.desc == Group.ADMIN)
            is_teacher = (group.desc == Group.TEACHER)
            is_student = (group.desc == Group.STUDENT)


    return {"layout" : logged_layout(),
            "custom_scripts" : custom_scripts, 
            "base_to_full" : cat.base_to_full, 
            "logged_in" : request.authenticated_userid,
	    "teacher_courses" : teacher_courses,
	    "student_courses" : student_courses,
            "is_guest" : is_guest, "is_admin" : is_admin, "is_teacher" : is_teacher, "is_student" : is_student,
            "page_title" : "Overview"
	     }


@view_config(route_name='learning', renderer='templates/new/learning.pt', permission='study')
def learning_view(request):
    custom_scripts = []
    return {"layout" : logged_layout(), 
            "base_to_full" : cat.base_to_full, 
            "custom_scripts" : custom_scripts,
	    "logged_in" : request.authenticated_userid,
	    "page_title" : "Learn By Example" }


@view_config(route_name='learning_reaction', renderer='templates/new/learning_reaction.pt', permission='study')
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
    custom_scripts = []
    custom_scripts.append('/bootstrap/js/learning_reactions.js')
    basename = request.matchdict["basename"]
    reaction = cat.get_reaction_by_basename(basename)

    return {"layout" : logged_layout(),
            "basename" : basename, 
	    "page_title" : reaction.full_name,
	    "custom_scripts" : custom_scripts,
            "full_name" : reaction.full_name, 
            "reaction_description" : reaction.desc, 
            "rgroups" : reaction.rgroups, 
            "logged_in" : request.authenticated_userid }


@view_config(route_name='img', permission='study')
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


@view_config(route_name='img_by_id', permission='study')
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

@view_config(route_name='img_from_history', permission='study')
def img_from_history_view(request):

    problem_id = request.matchdict["id"]
    which = request.matchdict["which"]

    response = None
    problem = None
    for p in history[request.authenticated_userid]:
        if p["problem_id"] == problem_id:
            problem = p
            print "Image: found problem in history"
            break


    if problem is not None:
        image = draw.renderReactionToBuffer(problem["instance_full"]).tostring()
        response = Response(content_type='image/png', body=image)
    else:
        response = HTTPNotFound()

    return response


@view_config(route_name='quiz_reactants', renderer='templates/new/quiz_reactants.pt', permission='study')
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
    custom_scripts = []
    custom_scripts.append("/bootstrap/js/quiz_reactants.js")
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
        instance_full = copy.deepcopy(instance)

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

        # record problem in history
        print "Adding problem " + problem_id + " to " + request.authenticated_userid + "'s history as incomplete"
        if request.authenticated_userid not in history:
            history[request.authenticated_userid] = []
        history[request.authenticated_userid].append({'problem_id' : problem_id,
                                                      'type' : 'reactants',
                                                      'status' : 'incomplete',
                                                      'basename' : basename,
                                                      'instance_full' : instance_full,
                                                      'instance_part' : instance, })

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

            problem_h = None
            for p in history[request.authenticated_userid]:
                    if p['problem_id'] == problem_id:
                        problem_h = p
                        break

            if problem_h == None:
                print "Error: could not find problem in history"

            if set(ans) != set(correctAnswers):
                message = "Wrong!"
                result = False
                #print "Your set: " + str(set(ans))
                #print "Good set: " + str(set(correctAnswers))

                # record result in history
                problem_h['status'] = 'fail'


            else:
                message = "Correct! You selected what's necessary and nothing else."
                result = True
                problem_h['status'] = 'pass'

            # Once user has made a choice, replace cut reaction with a full one
            quiz_problems[problem_id][0] = quiz_problems[problem_id][2]

    # prepare styles
    style_t = (
            "background-image: url('" + request.route_url("home") + "img/q_" + problem_id + "/",
            ".png');"
        )

     
    return {
            "layout": logged_layout(),
	    "custom_scripts" : custom_scripts,
	    "page_title" : full_name,
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


@view_config(route_name='quiz_products', renderer='templates/new/quiz_products.pt', permission='study')
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

        instance_full = copy.deepcopy(instance)

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

        # record problem in history
        print "Adding problem " + problem_id + " to " + request.authenticated_userid + "'s history as incomplete"
        if request.authenticated_userid not in history:
            history[request.authenticated_userid] = []
        history[request.authenticated_userid].append({'problem_id' : problem_id,
                                                      'type' : 'products',
                                                      'status' : 'incomplete',
                                                      'basename' : basename,
                                                      'instance_full' : instance_full,
                                                      'instance_part' : instance })

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

            problem_h = None
            for p in history[request.authenticated_userid]:
                    if p['problem_id'] == problem_id:
                        problem_h = p
                        break

            if set(ans) != set(correctAnswers):
                message = "Wrong!"
                result = False
                problem_h['status'] = 'fail'
                #print "Your set: " + str(set(ans))
                #print "Good set: " + str(set(correctAnswers))
            else:
                message = "Correct! You selected what's necessary and nothing else."
                result = True
                problem_h['status'] = 'pass'

            # Once user has made a choice, replace cut reaction with a full one
            
            quiz_problems[problem_id][0] = quiz_problems[problem_id][2]

    # prepare styles
    style_t = (
            "background-image: url('" + request.route_url("home") + "img/q_" + problem_id + "/",
            ".png');"
        )

     
    return {
            "layout": logged_layout(),
            "basename" : basename,
	    "page_title" : full_name,
            "full_name" : full_name,
            "problem_id" : problem_id,
            "indeces" : range(0, len(quiz_problems[problem_id][1])),
            "style_t" : style_t,
            "message" : message,
            "result" : result,
            "state" : state,
            "logged_in" : request.authenticated_userid 
        }


@view_config(route_name='quiz_reaction', renderer='templates/quiz_reaction.pt', permission='study')
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

        # prepare instance
        instance = reaction.getInstance()
        mainImage = draw.renderReactionToBuffer(instance).tostring()

        quiz_problems[problem_id] = (mainImage, basename, full_name)

        # record problem in history
        print "Adding problem " + problem_id + " to " + request.authenticated_userid + "'s history as incomplete"
        if request.authenticated_userid not in history:
            history[request.authenticated_userid] = []
        history[request.authenticated_userid].append({'problem_id' : problem_id,
                                                      'type' : session['quiz_type'],
                                                      'status' : 'incomplete',
                                                      'basename' : basename,
                                                      'instance_full' : instance,
                                                      'instance_part' : instance })

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

            problem_h = None
            for p in history[request.authenticated_userid]:
                if p['problem_id'] == problem_id:
                    problem_h = p
                    break

            if problem_h == None:
                print "Error: could not find problem in history"

            if correctAnswer != ans:
                message = "Wrong! This is actually " + quiz_problems[problem_id][2]
                result = False
                problem_h['status'] = 'fail'
                #print "Your set: " + str(set(ans))
                #print "Good set: " + str(set(correctAnswers))
            else:
                message = "Correct! This indeed is " + quiz_problems[problem_id][2]
                result = True
                problem_h['status'] = 'pass'

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

@view_config(route_name='quiz_history', renderer='templates/quiz_history.pt', permission='study')
def quiz_history_view(request):
    reactants_pass = []
    reactants_fail = []
    reactants_inc = []
    products_pass = []
    products_fail = []
    products_inc = []
    reactions_pass = []
    reactions_fail = []
    reactions_inc = []
    rest = []

    for p in history[request.authenticated_userid]:
        if p['type'] == 'reactants' and p['status'] == 'pass':
            reactants_pass.append(p)
        elif p['type'] == 'reactants' and p['status'] == 'fail':
            reactants_fail.append(p)
        elif p['type'] == 'reactants' and p['status'] == 'incomplete':
            reactants_inc.append(p)
        elif p['type'] == 'products' and p['status'] == 'pass':
            products_pass.append(p)
        elif p['type'] == 'products' and p['status'] == 'fail':
            products_fail.append(p)
        elif p['type'] == 'products' and p['status'] == 'incomplete':
            products_inc.append(p)
        elif p['type'] == 'reaction' and p['status'] == 'pass':
            reactions_pass.append(p)
        elif p['type'] == 'reaction' and p['status'] == 'fail':
            reactions_fail.append(p)
        elif p['type'] == 'reaction' and p['status'] == 'incomplete':
            reactions_inc.append(p)
        else:
            rest.append(p)

    total = len(reactants_pass) + len(reactants_fail) + len(reactants_inc) + len(products_pass) + len(products_fail) + len(products_inc) + len(reactions_pass) + len(reactions_fail) + len(reactions_inc)

    total_pass = len(reactants_pass) + len(products_pass) + len(reactions_pass)
    total_fail = len(reactants_fail) + len(products_fail) + len(reactions_fail)
    total_inc = len(reactants_inc) + len(products_inc) + len(reactions_inc)
    total_orphans = len(rest)

    overall_success = 0
    if total_fail + total_pass > 0:
        overall_success = 100 * total_pass / (total_fail + total_pass)

    return {
            "total" : total,
            "total_pass" : total_pass,
            "total_fail" : total_fail,
            "total_inc" : total_inc,
            "total_orphans" : total_orphans,
            "overall_success" : overall_success,
            "reactants_pass" : reactants_pass,
            "reactants_fail" : reactants_fail,
            "reactants_inc" : reactants_inc,
            "products_pass" : products_pass,
            "products_fail" : products_fail,
            "products_inc" : products_inc,
            "reactions_pass" : reactions_pass,
            "reactions_fail" : reactions_fail,
            "reactions_inc" : reactions_inc,
            "rest" : rest,

            "layout": site_layout(),
            "logged_in" : request.authenticated_userid 
        }


@view_config(route_name='synthesis', renderer='templates/new/synthesis.pt', permission='study')
def synthesis_view(request):
    custom_scripts = []
    return {"layout": logged_layout(),
            "custom_scripts" : custom_scripts,
	    "logged_in" : request.authenticated_userid,
	    "page_title" : "Multistep Synthesis"	 }

@view_config(route_name='addreaction', renderer='templates/new/addreaction.pt', permission='study')
def addreaction_view(request):
    custom_scripts = []
    return {"layout": logged_layout(),
	    "custom_scripts" : custom_scripts,
            "logged_in" : request.authenticated_userid,
	    "page_title" : "Add New Reaction"			 }


@view_config(route_name='about', renderer='templates/new/about.pt', permission='study')
def about_view(request):
    custom_scripts = []
    return {"layout": logged_layout(),
            "custom_scripts" : custom_scripts,
            "logged_in" : request.authenticated_userid, 
	    "page_title" : "About Us"		}

@view_config(route_name='select_quiz', renderer='templates/new/select_quiz.pt', permission='study')
def select_quiz_view(request):
    custom_scripts = []

    return {"layout": logged_layout(),
            "custom_scripts" : custom_scripts,
	    "base_to_full" : cat.base_to_full,
            "logged_in" : request.authenticated_userid,
            "page_title" : "Select Quiz"           }

@view_config(route_name='createcourse', renderer='templates/new/createcourse.pt', permission='study')
def create_course_view(request):

    custom_scripts = []
    message = ""
    class_title = ""   
    course_description = ""
    currentuser = DBSession.query(User).filter(User.username == request.authenticated_userid).first() 
    courses = DBSession.query(Course).filter(Course.owner == currentuser.id).all()
    
    if 'submit.createcourse' in request.params:
	 class_title = request.params['class_title']
	 course_description = request.params['course_description']
	 new_course_code = str(uuid.uuid4())[0:16].upper()  # or whatever
 	 
	 if DBSession.query(Course).filter_by(name=class_title).first() is None:
               DBSession.add(Course(name=class_title, owner=currentuser.id, description=course_description,  access_code=new_course_code))
               message = "Class " + class_title + " has been added"
               courses = DBSession.query(Course).filter(Course.owner == currentuser.id).all()
	 else:
               message = "Class Title " + class_title + " already exists"
 
    return {"layout": logged_layout(),
            "logged_in" : request.authenticated_userid,
            "message" : message,
            "custom_scripts" : custom_scripts,
	    "courses" : courses,
	    "page_title" : "Create Class"           }

@view_config(route_name='course_signup', renderer='templates/new/course_signup.pt', permission='study')
def course_signup_view(request):

    custom_scripts = []
    message = ""
    access_code = ""
    currentuser = DBSession.query(User).filter(User.username == request.authenticated_userid).first()
    
    print "######################## " + str(currentuser.id) + " ###########################" 
    enrolls = DBSession.query(Enrolled).filter(Enrolled.userid == currentuser.id ).all()
    courses =  DBSession.query(Course,Enrolled,User).filter(Course.id==Enrolled.courseid).filter(Enrolled.userid==currentuser.id).filter(Course.id==User.id).all()
    
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
		courses = DBSession.query(Course,Enrolled,User).filter(Course.id==Enrolled.courseid).filter(Enrolled.userid==currentuser.id).filter(Course.id==User.id).all()
	    else: 
		message = "You are already enrolled in the Course"
		


    return {"layout": logged_layout(),
            "logged_in" : request.authenticated_userid,
            "custom_scripts" : custom_scripts,
	    "message" : message,
	    "courses" : courses,
	    "page_title" : "Signup to a Course"           }



@view_config(route_name='contact', renderer='templates/new/contact.pt', permission='study')
def contact_view(request):
    custom_scripts = []
    state = "new form"
    if "txtComment" in request.POST:
        state = "sent"        
        with open("contact.txt", "a") as myfile:
            myfile.write(str(datetime.datetime.now()) + "\n")
            myfile.write("-------MESSAGE--------\n")
            myfile.write(request.POST["txtComment"] + "\n")
            myfile.write("----END OF MESSAGE----\n\n")


    return {"layout": logged_layout(),
            "custom_scripts" : custom_scripts, 
            "state" : state,
            "logged_in" : request.authenticated_userid,
	    "page_title" : "Contact Us"			}


@view_config(route_name='student_register', renderer='templates/new/student_register.pt')
def student_register_view(request):
    

    message= ""
    username = ""
    first_name = ""
    last_name = ""
    student_number = ""
    email = "" 
    password = ""
    confirm_password = ""
    
    if 'form_register.submitted' in request.params: 
        first_name = request.params['first_name']
	username = request.params['username']
        last_name = request.params['last_name']
  	student_number = request.params['student_number']
	email = request.params['email']
	password = request.params['password']
	confirm_password = request.params['confirm_password']
	
	
	if len(first_name) <= 0 & len(last_name) <= 0:
		message = "Missing inputs"
	else:
	    if password <> confirm_password: 
		 message = "Passwords are not matching"
	
	# Check if there are no existing usernames  
	if DBSession.query(User).filter_by(username=username).first() is None:
            DBSession.add(User(username=username, email=email, firstname=first_name, lastname=last_name, group=4, phash=getHash(password)))
            message = "User '" + username + "' has been added"
        else:
            message = "User '" + username + "' already exists"
	

 
    # there can not be two of the same emails return a message user has been registered 

    # both password and confirm password must be the same or else return a message 

   
    return {"layout": main_layout(),
	    "message": message
	   } 

@view_config(route_name='select_register', renderer='templates/new/select_register.pt')
def select_register_view(request):
    return {"layout": main_layout()
            }


@view_config(route_name='login', renderer='templates/new/login.pt')
@forbidden_view_config(renderer='templates/new/login.pt')
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
