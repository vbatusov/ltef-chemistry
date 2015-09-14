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


def site_layout():
    renderer = get_renderer("ltefserver:templates/layout.pt")
    layout = renderer.implementation().macros['layout']
    return layout


@view_config(route_name='quiz_reaction', renderer='ltefserver:templates/quiz_reaction.pt', permission='study')
def quiz_reaction_view(request):
    global quiz_problems
    session = request.session

    problem_id = ""
    basename = ""
    full_name = ""
    message = ""
    result = False
    state = "ask"
    group = group_security(request.authenticated_userid)

    # Generate a problem, store the objects, present to user
    if 'quiz_type' not in session or session['quiz_type'] != 'reaction' or session['problem_id'] not in quiz_problems.keys():
        session.invalidate()
        problem_id = str(uuid.uuid4())
        session['quiz_type'] = 'reaction'
        session['problem_id'] = problem_id
        state = "ask"
        custom_scripts = []
        # select a reaction randomly
        basename = random.choice(cat.get_sorted_basenames())
        reaction = cat.get_reaction_by_basename(basename)
        full_name = reaction.full_name

        # prepare instance
        instance = reaction.getInstance()
        mainImage = draw.renderReactionToBuffer(instance, layout=True).tostring()

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

    owner_courses = []
    enrolled_courses = []
    if group["is_teacher"]:
        owner_courses = Course.owner_courses(request.authenticated_userid)
    elif group["is_student"]:
        enrolled_courses = Enrolled.enrolled_courses(request.authenticated_userid)

    return {
            "layout": logged_layout(),
            "basename" : "unknown_reaction",
            "custom_scripts" : "custom_scripts",
            "full_name" : "Unknown Reaction",
            "is_admin" : group["is_admin"], "is_teacher" : group["is_teacher"], "is_student" : group["is_student"],
            "problem_id" : problem_id,
            "page_title" : "Unknown Reaction",
            "message" : message,
            "result" : result,
            "state" : state,
            "owner_courses" : owner_courses,
            "enrolled_courses" : enrolled_courses,
            "base_to_full" : cat.base_to_full,
            "logged_in" : request.authenticated_userid
        }


@view_config(route_name='quiz', match_param='quiz_type=reactants', renderer='ltefserver:templates/new/quiz_reactant_reaction.pt', permission='study')
def quiz_reactant_view(request):

    class_name = request.matchdict["course"]
    chapter_name = request.matchdict["chapter"]
    mode = request.matchdict["basename"]
    reaction_type = request.matchdict["quiz_type"]
    currentuser = User.current_user(request.authenticated_userid)
    group = group_security(request.authenticated_userid)

    if group["is_teacher"]:
         course = DBSession.query(Course).filter(Course.name == class_name, Course.owner == currentuser.id ).first()
    elif group["is_student"]:
        course = DBSession.query(Course).filter(Enrolled.courseid == Course.id).filter(Enrolled.userid == currentuser.id).filter(Course.name == class_name).first()

    chapter = DBSession.query(Chapter).filter( Chapter.title == chapter_name, Chapter.course == course.id  ).first()

    global quiz_problems
    session = request.session
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

        fullImage = draw.renderReactionToBuffer(instance, layout=True).tostring()

        reactants = instance.reactants
	print reactants.__str__()
        molecule = chem.Molecule()
        molecule.addAtom(chem.Atom("?", 0, 0, 0, 0, 0))

        instance.reactants = [molecule]

        # Reaction image without reactants
        mainImage = draw.renderReactionToBuffer(instance, layout=True).tostring()

        reactantImages = []
        for mol in reactants:
            image = draw.renderMoleculeToBuffer(mol, layout=True).tostring()
            reactantImages.append([image, True])    # indicate that these are correct answers


        # Generate wrong answers here, add to reactantImages
        for mol in chem.mutateMolecules(reactants):
            image = draw.renderMoleculeToBuffer(mol, layout=True).tostring()
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
		DBSession.add(Quiz_history( course = course.id, chapter = chapter.id, user = currentuser.id, score=0, reaction_name = mode, quiz_type=quiz_type))

            else:
                message = "Correct! You selected what's necessary and nothing else."
                result = True
                problem_h['status'] = 'pass'
		DBSession.add(Quiz_history( course = course.id,  chapter = chapter.id, user = currentuser.id, score=1, reaction_name = mode, quiz_type=quiz_type))


            # Once user has made a choice, replace cut reaction with a full one
            quiz_problems[problem_id][0] = quiz_problems[problem_id][2]

    # prepare styles
    style_t = (
            "background-image: url('" + request.route_url("home") + "img/q_" + problem_id + "/",
            ".png');"
        )

    owner_courses = []
    enrolled_courses = []
    if group["is_teacher"]:
        owner_courses = Course.owner_courses(request.authenticated_userid)
    elif group["is_student"]:
        enrolled_courses = Enrolled.enrolled_courses(request.authenticated_userid)

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
            "is_admin" : group["is_admin"], "is_teacher" : group["is_teacher"], "is_student" : group["is_student"],
            "state" : state,
            "owner_courses" : owner_courses,
            "enrolled_courses" : enrolled_courses,
            "logged_in" : request.authenticated_userid
        }

@view_config(route_name='quiz', match_param='quiz_type=products', renderer='ltefserver:templates/new/quiz_product_reaction.pt', permission='study')
def quiz_product_view(request):

    class_name = request.matchdict["course"]
    chapter_name = request.matchdict["chapter"]
    mode  = request.matchdict["basename"]
    quiz_type = request.matchdict["quiz_type"]

    currentuser = User.current_user(request.authenticated_userid)

    group = group_security(request.authenticated_userid)
    if group["is_teacher"]:
         course = DBSession.query(Course).filter(Course.name == class_name, Course.owner == currentuser.id ).first()
    elif group["is_student"]:
        course = DBSession.query(Course).filter(Enrolled.courseid == Course.id).filter(Enrolled.userid == currentuser.id).filter(Course.name == class_name).first()

    chapter = DBSession.query(Chapter).filter( Chapter.title == chapter_name, Chapter.course == course.id  ).first()


    custom_scripts = []
    custom_scripts.append("/bootstrap/js/quiz_reactants.js")
    global quiz_problems
    session = request.session
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

        fullImage = draw.renderReactionToBuffer(instance, layout=True).tostring()

        products = instance.products

        molecule = chem.Molecule()
        molecule.addAtom(chem.Atom("?", 0, 0, 0, 0, 0))

        instance.products = [molecule]

        # Reaction image without products
        mainImage = draw.renderReactionToBuffer(instance, layout=True).tostring()

        reactantImages = []
        for mol in products:
            image = draw.renderMoleculeToBuffer(mol, layout=True).tostring()
            reactantImages.append([image, True])    # indicate that these are correct answers


        # Generate wrong answers here, add to reactantImages
        for mol in chem.mutateMolecules(products):
            image = draw.renderMoleculeToBuffer(mol, layout=True).tostring()
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
		DBSession.add(Quiz_history( course = course.id, chapter = chapter.id, user = currentuser.id, score=0, reaction_name = mode, quiz_type=quiz_type))
            else:
                message = "Correct! You selected what's necessary and nothing else."
                result = True
                problem_h['status'] = 'pass'
	        DBSession.add(Quiz_history( course=course.id, chapter = chapter.id, user = currentuser.id, score=1, reaction_name = mode, quiz_type=quiz_type))
            # Once user has made a choice, replace cut reaction with a full one

            quiz_problems[problem_id][0] = quiz_problems[problem_id][2]

    # prepare styles
    style_t = (
            "background-image: url('" + request.route_url("home") + "img/q_" + problem_id + "/",
            ".png');"
        )


    owner_courses = []
    enrolled_courses = []
    if group["is_teacher"]:
        owner_courses = Course.owner_courses(request.authenticated_userid)
    elif group["is_student"]:
        enrolled_courses = Enrolled.enrolled_courses(request.authenticated_userid)

    return {
            "layout": logged_layout(),
            "basename" : basename,
            "page_title" : full_name,
            "custom_scripts" : custom_scripts,
            "full_name" : full_name,
            "problem_id" : problem_id,
            "indeces" : range(0, len(quiz_problems[problem_id][1])),
            "style_t" : style_t,
            "message" : message,
            "result" : result,
            "state" : state,
            "owner_courses" : owner_courses,
            "enrolled_courses" : enrolled_courses,
            "is_admin" : group["is_admin"], "is_teacher" : group["is_teacher"], "is_student" : group["is_student"],
            "logged_in" : request.authenticated_userid
        }

@view_config(route_name='quiz_question', renderer='ltefserver:templates/new/quiz_question.pt', permission='educate')
def quiz_question_view(request):

    course_name = request.matchdict["course"]
    student_username = request.matchdict["student"]
    quiz_type = request.matchdict["quiz"]
    chapter_name = request.matchdict["chapter"]

    message = ""
    custom_scripts =[]

    current_user = DBSession.query(User).filter(User.username == request.authenticated_userid).first()
    group = group_security(request.authenticated_userid)

    owner_courses = []
    enrolled_courses = []
    if group["is_teacher"]:
        owner_courses = Course.owner_courses(request.authenticated_userid)
    elif group["is_student"]:
        enrolled_courses = Enrolled.enrolled_courses(request.authenticated_userid)

    student = DBSession.query(User).filter(User.username == student_username).first()
    quiz = DBSession.query(Quiz_history).filter(Quiz_history.student == student.id).filter(Quiz_history.course == course.id).filter(Quiz_history.chapter == chapter.id).filter(Quiz_history.id == quiz).first()





    return {"layout": logged_layout(),
            "logged_in" : request.authenticated_userid,
            "message" : message,
            "owner_courses" : owner_courses,
            "enrolled_courses" : enrolled_courses,
            "custom_scripts" : custom_scripts,
            "is_admin" : group["is_admin"], "is_teacher" : group["is_teacher"], "is_student" : group["is_student"],
            "page_title" : student.firstname.title() + " " + student.lastname.title() + " " + "Quiz History"           }





@view_config(route_name='student_quiz_history', renderer='ltefserver:templates/new/student_quiz_history.pt', permission='educate')
def student_quiz_history_view(request):


    course_name = request.matchdict["course"]
    student_username = request.matchdict["student"]
    custom_scripts = []
    message = ""
    chapter_title = ""
    course_description = ""
    currentuser = DBSession.query(User).filter(User.username == request.authenticated_userid).first()
    group = group_security(request.authenticated_userid)

    if group["is_teacher"]:
         course = DBSession.query(Course).filter(Course.name == course_name, Course.owner == currentuser.id ).first()
    elif group["is_student"]:
        course = DBSession.query(Course).filter(Enrolled.courseid == Course.id).filter(Enrolled.userid == currentuser.id).filter(Course.name == course_name).first()

    student = DBSession.query(User).filter(User.username == student_username).first()
    quiz_histories = DBSession.query(Quiz_history, Chapter).filter(Quiz_history.user == student.id).filter(Quiz_history.course == course.id).filter(Chapter.id == Quiz_history.chapter).all()

    owner_courses = []
    enrolled_courses = []
    if group["is_teacher"]:
        owner_courses = Course.owner_courses(request.authenticated_userid)
    elif group["is_student"]:
        enrolled_courses = Enrolled.enrolled_courses(request.authenticated_userid)

    return {"layout": logged_layout(),
            "logged_in" : request.authenticated_userid,
            "message" : message,
            "owner_courses" : owner_courses,
            "enrolled_courses" : enrolled_courses,
            "custom_scripts" : custom_scripts,
	        "quiz_histories" : quiz_histories,
            "is_admin" : group["is_admin"], "is_teacher" : group["is_teacher"], "is_student" : group["is_student"],
            "page_title" : student.firstname.title() + " " + student.lastname.title() + " " + "Quiz History"           }


@view_config(route_name='select_quiz', renderer='ltefserver:templates/new/select_quiz.pt', permission='study')
def select_quiz_view(request):
    custom_scripts = []
    group = group_security(request.authenticated_userid)

    quiz_type = ""
    reaction_selector = ""

    if 'submit.selected_quiz' in request.params:

        quiz_type = request.params['quiz_type']
        reaction_selector = request.params['reaction_selector']
	url = request.route_url(quiz_type, basename=reaction_selector )
	return HTTPFound(location=url)

    owner_courses = []
    enrolled_courses = []
    if group["is_teacher"]:
        owner_courses = Course.owner_courses(request.authenticated_userid)
    elif group["is_student"]:
        enrolled_courses = Enrolled.enrolled_courses(request.authenticated_userid)

    return {"layout": logged_layout(),
            "custom_scripts" : custom_scripts,
	        "base_to_full" : cat.base_to_full,
            "owner_courses" : owner_courses,
            "enrolled_courses" : enrolled_courses,
            "logged_in" : request.authenticated_userid,
            "is_admin" : group["is_admin"], "is_teacher" : group["is_teacher"], "is_student" : group["is_student"],
	        "page_title" : "Select Quiz"           }




@view_config(route_name='select_reaction_quiz', renderer='ltefserver:templates/new/select_reaction_quiz.pt', permission='study')
def select_reaction_quiz_view(request):
    custom_scripts = []
    group = group_security(request.authenticated_userid)

    quiz_type = ""
    reaction_selector = ""

    if 'quiz_type' in request.params:
        return HTTPFound(location=request.route_url('quiz', course=request.matchdict["course"], chapter=request.matchdict["chapter"], quiz_type=request.params['quiz_type'], basename=request.matchdict["basename"]  ))

    owner_courses = []
    enrolled_courses = []
    if group["is_teacher"]:
        owner_courses = Course.owner_courses(request.authenticated_userid)
    elif group["is_student"]:
        enrolled_courses = Enrolled.enrolled_courses(request.authenticated_userid)

    return {"layout": logged_layout(),
            "custom_scripts" : custom_scripts,
            "base_to_full" : cat.base_to_full,
            "owner_courses" : owner_courses,
            "enrolled_courses" : enrolled_courses,
            "logged_in" : request.authenticated_userid,
            "is_admin" : group["is_admin"], "is_teacher" : group["is_teacher"], "is_student" : group["is_student"],
            "page_title" : "Select Quiz"           }


@view_config(route_name='quiz_history', renderer='ltefserver:templates/quiz_history.pt', permission='study')
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


@view_config(route_name='quiz_products', renderer='ltefserver:templates/new/quiz_products.pt', permission='study')
def quiz_products_view(request):
    custom_scripts = []
    custom_scripts.append("/bootstrap/js/quiz_reactants.js")
    global quiz_problems
    session = request.session
    group = group_security(request.authenticated_userid)
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

        fullImage = draw.renderReactionToBuffer(instance, layout=True).tostring()

        reactants = instance.reactants
        products = instance.products

        molecule = chem.Molecule()
        molecule.addAtom(chem.Atom("?", 0, 0, 0, 0, 0))

        instance.products = [molecule]

        # Reaction image without products
        mainImage = draw.renderReactionToBuffer(instance, layout=True).tostring()

        reactantImages = []
        for mol in products:
            image = draw.renderMoleculeToBuffer(mol, layout=True).tostring()
            reactantImages.append([image, True])    # indicate that these are correct answers


        # Generate wrong answers here, add to reactantImages

        bastardReaction = chem.bastardReaction(reactants, products)

        for mol in bastardReaction.mutateMolecules(products):
            image = draw.renderMoleculeToBuffer(mol, layout=True).tostring()
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


    owner_courses = []
    enrolled_courses = []
    if group["is_teacher"]:
        owner_courses = Course.owner_courses(request.authenticated_userid)
    elif group["is_student"]:
        enrolled_courses = Enrolled.enrolled_courses(request.authenticated_userid)

    return {
            "layout": logged_layout(),
            "basename" : basename,
    	    "page_title" : full_name,
      	    "custom_scripts" : custom_scripts,
            "full_name" : full_name,
            "problem_id" : problem_id,
            "indeces" : range(0, len(quiz_problems[problem_id][1])),
            "style_t" : style_t,
            "message" : message,
            "result" : result,
            "state" : state,
            "owner_courses" : owner_courses,
            "enrolled_courses" : enrolled_courses,
            "is_admin" : group["is_admin"], "is_teacher" : group["is_teacher"], "is_student" : group["is_student"],
            "logged_in" : request.authenticated_userid
        }


@view_config(route_name='quiz_reactants', renderer='ltefserver:templates/new/quiz_reactants.pt', permission='study')
def quiz_reactants_view(request):
    global quiz_problems
    session = request.session

    group = group_security(request.authenticated_userid)
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

        fullImage = draw.renderReactionToBuffer(instance, layout=True).tostring()

        reactants = instance.reactants
	products = instance.products
        molecule = chem.Molecule()
        molecule.addAtom(chem.Atom("?", 0, 0, 0, 0, 0))

        instance.reactants = [molecule]

        # Reaction image without reactants
        mainImage = draw.renderReactionToBuffer(instance, layout=True).tostring()

        reactantImages = []
        for mol in reactants:
            image = draw.renderMoleculeToBuffer(mol, layout=True).tostring()
            reactantImages.append([image, True])    # indicate that these are correct answers

	bastardReaction = chem.bastardReaction(reactants, products)
        # Generate wrong answers here, add to reactantImages
        for mol in bastardReaction.mutateMolecules(reactants):
            image = draw.renderMoleculeToBuffer(mol, layout=True).tostring()
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

    owner_courses = []
    enrolled_courses = []
    if group["is_teacher"]:
        owner_courses = Course.owner_courses(request.authenticated_userid)
    elif group["is_student"]:
        enrolled_courses = Enrolled.enrolled_courses(request.authenticated_userid)

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
            "is_admin" : group["is_admin"], "is_teacher" : group["is_teacher"], "is_student" : group["is_student"],
            "state" : state,
            "owner_courses" : owner_courses,
            "enrolled_courses" : enrolled_courses,
            "logged_in" : request.authenticated_userid
        }




@view_config(route_name='img', permission='study')
def img_view(request):

    param_str = request.matchdict["filename"]
    mode = request.matchdict["what"]
    basename = request.matchdict["basename"]

    reaction = cat.get_reaction_by_basename(basename)

    response = None

    # Renders a generic reaction from catalog
    if mode == "generic":
        response = Response(content_type='image/png', body=draw.renderReactionToBuffer(reaction, layout=False).tostring())

    # Renders an instance generated from generic using parameters
    elif mode == "instance":
        instance = reaction.getInstance()
        response = Response(content_type='image/png', body=draw.renderReactionToBuffer(instance, layout=True).tostring())

    # Renders a generic r-group molecule using params
    elif mode == "rgroup":
        params = param_str.split(",")
        # first arg is "R1", "R2", etc.
        # second arg is the list index of specific molecule which the group could be
        # e.g. "...?R1,0" is for the first choice of R1
        if len(params) == 2:
            buf = draw.renderRGroupToBuffer(reaction, params[0].upper(), int(params[1]), layout=True)
            if buf is not None:
                response = Response(content_type='image/png', body=buf.tostring())

    # Renders an instance without reactants
    elif mode == "noreactants":
        instance = reaction.getInstance()
        instance.reactants = []
        response = Response(content_type='image/png', body=draw.renderReactionToBuffer(instance, layout=True).tostring())

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
        image = draw.renderReactionToBuffer(problem["instance_full"], layout=True).tostring()
        response = Response(content_type='image/png', body=image)
    else:
        response = HTTPNotFound()

    return response
