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
    Quiz_history,
    Generated_question,
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
import distractor




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

instance_reaction = None
instance_choices = []

question_svg = ""

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

    basename = ""
    page_title = ""
    message = ""
    owner_courses = []
    enrolled_courses = []
    class_name = request.matchdict["course"]
    chapter_name = request.matchdict["chapter"]
    mode = request.matchdict["basename"]
    reaction_type = request.matchdict["quiz_type"]
    currentuser = User.current_user(request.authenticated_userid)
    mol_choices_svg = []
    # Two type of states Ask the question or Tell if answer by result being correct or incorrect
    state = ""
    result = False

    custom_scripts = []
    custom_scripts.append("/bootstrap/js/quiz_reactants.js")

    # Get the users security group
    group = group_security(request.authenticated_userid)
    if group["is_teacher"]:
        owner_courses = Course.owner_courses(request.authenticated_userid)
        course = DBSession.query(Course).filter(Course.name == class_name, Course.owner == currentuser.id ).first()
    elif group["is_student"]:
        enrolled_courses = Enrolled.enrolled_courses(request.authenticated_userid)
        course = DBSession.query(Course).filter(Enrolled.courseid == Course.id).filter(Enrolled.userid == currentuser.id).filter(Course.name == class_name).first()

    # Get the current Chapter being used
    chapter = DBSession.query(Chapter).filter( Chapter.title == chapter_name, Chapter.course == course.id ).first()

    # Where to store the generated un answered question ? Will be stored in Gerenated_question database table
        # Gerenated_question id, user, quiz_type, full_reaction, choices
    generated_question = DBSession.query(Generated_question).filter(Generated_question.chapter == chapter.id).filter(Generated_question.user == currentuser.id).filter(Generated_question.quiz_type == reaction_type).first()

    reaction_svg = ""
    question_svg = ""
    choices_svg = []

    # if a current_user has no generated question then generate a reaction question
    if generated_question is None:

        # change state to ask
        state = "ask"

        # if mode is random select a reaction randomly
        if mode == "random":
            basename = random.choice(cat.get_sorted_basenames())
        else:
            basename = mode

        # retrieve the reaction
        reaction = cat.get_reaction_by_basename(basename)
        reac_id = DBSession.query(Reac).filter(Reac.basename == basename ).first().id

        custom_reaction = DBSession.query(Customizable_reaction).filter(Customizable_reaction.chapter == chapter.id ).filter(Customizable_reaction.reaction == reac_id ).first()

        # Get it's full reaction name
        page_title = custom_reaction.title

        # prepare full reaction instance
        instance_full_reaction = reaction.getInstance()
        instance_reaction = copy.deepcopy(instance_full_reaction)

        # prepare reactants and products instances
        reactants = instance_full_reaction.reactants
        products = instance_full_reaction.products

        # Initialize draw SVGRenderer object
        svg_reanderer = draw.SVGRenderer()

        # Hide the reactant from the Question and add a question mark
        molecule = chem.Molecule()
        molecule.addAtom(chem.Atom("?", 0, 0, 0, 0, 0))
        instance_full_reaction.reactants = [molecule]

        # render image svg without reactants
        question_svg = ""
        question_svg = svg_reanderer.renderReactionToBuffer(instance_full_reaction, layout=False)
        question_svg = update_svg_size(question_svg, '100%', '-1')

        instance_choices = []

        # Add all the correct choices to instance_choices
        for molecule in reactants:
            instance_choices.append([molecule, True])

        # Initializes object DistractorReaction to generate wrong answers
        distractor_reaction = distractor.DistractorReaction(reactants, products)

        # Add all the incorrect choices to instance_choices
        for molecule in distractor_reaction.generate_reactant_distractors():
            instance_choices.append([molecule, False])

        # shuffle the molecule choices
        random.shuffle(instance_choices)

        choices_svg = []
        # Draw the molecule choices and store the correct choices in a global set correct_choices
        for index in range(0,  len(instance_choices)):
            svg = svg_reanderer.renderMoleculeToBuffer(instance_choices[index][0], layout=False)
            svg = update_svg_size(svg, '100%', '100%')
            choices_svg.append([svg, instance_choices[index][1]])    # indicate that these are correct answers

        DBSession.add(Generated_question( user = currentuser.id, chapter = chapter.id , quiz_type = reaction_type, reaction = reac_id, full_reaction = instance_reaction, choices = instance_choices ))
    # elif a current_user has answered the question remove the generated question and tell the result

    elif generated_question is not None and "answer" in request.GET:

        # change state to tell user the result
        state = 'tell'

        # get the anser provided by the user
        answer = request.GET["answer"].split(",")

        custom_reaction = DBSession.query(Customizable_reaction).filter(Customizable_reaction.chapter == chapter.id ).filter(Customizable_reaction.reaction == generated_question.reaction ).first()

        # Get it's full reaction name
        page_title = custom_reaction.title

        # recover the generated question
        instance_full_reaction = generated_question.full_reaction # get the full reaction that has been generated
        instance_choices = generated_question.choices # get the multiple choices generated

        # Initialize draw SVGRenderer object
        svg_reanderer = draw.SVGRenderer()

        reaction_svg = svg_reanderer.renderReactionToBuffer(instance_full_reaction, layout=False)
        reaction_svg = update_svg_size(reaction_svg, '100%', '-1') # update svg size to width to 100%

        # Remove the reactant with a question mark to display as the question
        instance_question = copy.deepcopy(instance_full_reaction)
        molecule = chem.Molecule()
        molecule.addAtom(chem.Atom("?", 0, 0, 0, 0, 0))
        instance_full_reaction.reactants = [molecule]

        # Initialize draw SVGRenderer object
        svg_reanderer = draw.SVGRenderer()

        # render instance question to image format svg
        question_svg = ""
        question_svg = svg_reanderer.renderReactionToBuffer(instance_full_reaction, layout=False)
        question_svg = update_svg_size(question_svg, '100%', '-1') # update svg size to width to 100%

        # get the correct_choices
        correct_choices = []
        for index in range(0,  len(instance_choices)):
            if instance_choices[index][1]:
                correct_choices.append(str(index))

        for instance_choice in instance_choices:
            instance_choice[1] = False

        for answer_index in answer:
            if answer_index != '':
                instance_choices[int(answer_index)][1] = True

        # check if the answer privided are correct or incorrect
        # Get the count of how many quiz histories there are.
        quiz_history_count = DBSession.query(Quiz_history).filter( Quiz_history.user == currentuser.id).filter(Quiz_history.course == course.id).filter(Quiz_history.chapter == chapter.id).count()
        quiz_history_count = quiz_history_count + 1

        if set(answer) != set(correct_choices):
            # record the answer to Quiz_history
            message = "Incorrect"
            result = False
            DBSession.add(Quiz_history( question_number = quiz_history_count, course = course.id, chapter = chapter.id, user = currentuser.id, score=0, reaction_name = custom_reaction.title, quiz_type=reaction_type, reaction_obj = instance_full_reaction, choice_obj = instance_choices ))
        else:
            # record the answer to Quiz_history
            message = "Correct"
            result = True
            DBSession.add(Quiz_history( question_number = quiz_history_count, course = course.id,  chapter = chapter.id, user = currentuser.id, score=1, reaction_name = custom_reaction.title, quiz_type=reaction_type, reaction_obj = instance_full_reaction, choice_obj = instance_choices))

        # Draw the molecules
        for mol in instance_choices:
    	    mol_choice_svg = svg_reanderer.renderMoleculeToBuffer(mol[0], layout=False )
    	    # Chop off the xml tag
            mol_choice_svg = mol_choice_svg[mol_choice_svg.find('\n') + 1:]
            # Modify height and width of the svg tag
            svgline = mol_choice_svg[:mol_choice_svg.find('\n')]
            svglineparts = re.split('height=".*?"', svgline)
            svgline = svglineparts[0] + 'height="100%" "' + svglineparts[1]
            svglineparts = re.split('width=".*?"', svgline)
            svgline = svglineparts[0] + 'width="100%" "' + svglineparts[1]
            mol_choice_svg = svgline + "\n" + mol_choice_svg[mol_choice_svg.find('\n') + 1 :]
    	    mol_choices_svg.append([mol_choice_svg, mol[1] ])    # indicate that these are wrong answers

        # remove the generated question from the Generated_question table
        DBSession.query(Generated_question).filter(Generated_question.id == generated_question.id).delete()

    # elif a current_user has a genereated question then ask the question again.
    elif generated_question is not None:

        # update state to ask user the question
        state = 'ask'

        custom_reaction = DBSession.query(Customizable_reaction).filter(Customizable_reaction.chapter == chapter.id ).filter(Customizable_reaction.reaction == generated_question.reaction ).first()

        # Get it's full reaction name
        page_title = custom_reaction.title

        instance_full_reaction = generated_question.full_reaction # get the full reaction that has been generated

        instance_choices = generated_question.choices # get the multiple choices generated

        # Remove the reactant with a question mark to display as the question
        instance_question = copy.deepcopy(instance_full_reaction)
        molecule = chem.Molecule()
        molecule.addAtom(chem.Atom("?", 0, 0, 0, 0, 0))
        instance_full_reaction.reactants = [molecule]

        # Initialize draw SVGRenderer object
        svg_reanderer = draw.SVGRenderer()

        # render instance question to image format svg
        question_svg = ""
        question_svg = svg_reanderer.renderReactionToBuffer(instance_full_reaction, layout=False)
        question_svg = update_svg_size(question_svg, '100%', '-1') # update svg size to width to 100%

        # render the instance_choices to image format svg
        choices_svg = []

        for index in range(0,  len(instance_choices)):
            svg = svg_reanderer.renderMoleculeToBuffer(instance_choices[index][0], layout=False)
            svg = update_svg_size(svg, '100%', '100%') # update svg size to height and width to 100%
            choices_svg.append([svg, instance_choices[index][1]])    # indicate that these are correct answers

    return {
            "layout": logged_layout(),
            "custom_scripts" : custom_scripts,
            "page_title" : page_title,
            "basename" : basename,
            "message" : message,
            "result" : result,
            "is_admin" : group["is_admin"], "is_teacher" : group["is_teacher"], "is_student" : group["is_student"],
            "state" : state,
            "owner_courses" : owner_courses,
            "enrolled_courses" : enrolled_courses,
            "logged_in" : request.authenticated_userid,
            "choices_svg" : choices_svg,
            "question_svg" : question_svg,
            "reaction_svg" : reaction_svg,
            "mol_choices_svg" : mol_choices_svg,
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



@view_config(route_name='quiz', match_param='quiz_type=products', renderer='ltefserver:templates/new/quiz_product_reaction.pt', permission='study')
def quiz_product_view(request):

    basename = ""
    page_title = ""
    message = ""
    owner_courses = []
    enrolled_courses = []
    class_name = request.matchdict["course"]
    chapter_name = request.matchdict["chapter"]
    mode = request.matchdict["basename"]
    reaction_type = request.matchdict["quiz_type"]
    currentuser = User.current_user(request.authenticated_userid)

    # Two type of states Ask the question or Tell if answer by result being correct or incorrect
    state = ""
    result = False

    custom_scripts = []
    custom_scripts.append("/bootstrap/js/quiz_reactants.js")

    # Get the users security group
    group = group_security(request.authenticated_userid)
    if group["is_teacher"]:
        owner_courses = Course.owner_courses(request.authenticated_userid)
        course = DBSession.query(Course).filter(Course.name == class_name, Course.owner == currentuser.id ).first()
    elif group["is_student"]:
        enrolled_courses = Enrolled.enrolled_courses(request.authenticated_userid)
        course = DBSession.query(Course).filter(Enrolled.courseid == Course.id).filter(Enrolled.userid == currentuser.id).filter(Course.name == class_name).first()

    # Get the current Chapter being used
    chapter = DBSession.query(Chapter).filter( Chapter.title == chapter_name, Chapter.course == course.id ).first()

    # Where to store the generated un answered question ? Will be stored in Gerenated_question database table
        # Gerenated_question id, user, quiz_type, full_reaction, choices
    generated_question = DBSession.query(Generated_question).filter(Generated_question.chapter == chapter.id).filter(Generated_question.user == currentuser.id).filter(Generated_question.quiz_type == reaction_type).first()

    reaction_svg = ""
    question_svg = ""
    choices_svg = []
    mol_choices_svg = []
    # if a current_user has no generated question then generate a reaction question
    if generated_question is None:

        # change state to ask
        state = "ask"

        # if mode is random select a reaction randomly
        if mode == "random":
            basename = random.choice(cat.get_sorted_basenames())
        else:
            basename = mode

        # retrieve the reaction
        reaction = cat.get_reaction_by_basename(basename)
        reac_id = DBSession.query(Reac).filter(Reac.basename == basename ).first().id

        custom_reaction = DBSession.query(Customizable_reaction).filter(Customizable_reaction.chapter == chapter.id ).filter(Customizable_reaction.reaction == reac_id ).first()

        # Get it's full reaction name
        page_title = custom_reaction.title

        # prepare full reaction instance
        instance_full_reaction = reaction.getInstance()
        instance_reaction = copy.deepcopy(instance_full_reaction)

        # prepare reactants and products instances
        reactants = instance_full_reaction.reactants
        products = instance_full_reaction.products

        # Initialize draw SVGRenderer object
        svg_reanderer = draw.SVGRenderer()

        # Hide the reactant from the Question and add a question mark
        molecule = chem.Molecule()
        molecule.addAtom(chem.Atom("?", 0, 0, 0, 0, 0))
        instance_full_reaction.products = [molecule]

        # render image svg without reactants
        question_svg = ""
        question_svg = svg_reanderer.renderReactionToBuffer(instance_full_reaction, layout=False)
        question_svg = update_svg_size(question_svg, '100%', '-1')

        instance_choices = []

        # Add all the correct choices to instance_choices
        for molecule in products:
            instance_choices.append([molecule, True])

        # Initializes object bastardReaction to generate wrong answers
        distractor_reaction = distractor.DistractorReaction(reactants, products)

        # Add all the incorrect choices to instance_choices
        for molecule in distractor_reaction.generate_product_distractors():
            instance_choices.append([molecule, False])

        # shuffle the molecule choices
        random.shuffle(instance_choices)

        choices_svg = []
        # Draw the molecule choices and store the correct choices in a global set correct_choices
        for index in range(0,  len(instance_choices)):
            svg = svg_reanderer.renderMoleculeToBuffer(instance_choices[index][0], layout=False)
            svg = update_svg_size(svg, '100%', '100%')
            choices_svg.append([svg, instance_choices[index][1]])    # indicate that these are correct answers

        DBSession.add(Generated_question( user = currentuser.id, chapter = chapter.id , quiz_type = reaction_type, reaction = reac_id, full_reaction = instance_reaction, choices = instance_choices ))
    # elif a current_user has answered the question remove the generated question and tell the result

    elif generated_question is not None and "answer" in request.GET:

        # change state to tell user the result
        state = 'tell'

        # get the anser provided by the user
        answer = request.GET["answer"].split(",")

        custom_reaction = DBSession.query(Customizable_reaction).filter(Customizable_reaction.chapter == chapter.id ).filter(Customizable_reaction.reaction == generated_question.reaction ).first()

        # Get it's full reaction name
        page_title = custom_reaction.title

        # recover the generated question
        instance_full_reaction = generated_question.full_reaction # get the full reaction that has been generated
        instance_choices = generated_question.choices # get the multiple choices generated

        # Initialize draw SVGRenderer object
        svg_reanderer = draw.SVGRenderer()

        reaction_svg = svg_reanderer.renderReactionToBuffer(instance_full_reaction, layout=False)
        reaction_svg = update_svg_size(reaction_svg, '100%', '-1') # update svg size to width to 100%

        # Remove the reactant with a question mark to display as the question
        instance_question = copy.deepcopy(instance_full_reaction)
        molecule = chem.Molecule()
        molecule.addAtom(chem.Atom("?", 0, 0, 0, 0, 0))
        instance_full_reaction.products = [molecule]

        # Initialize draw SVGRenderer object
        svg_reanderer = draw.SVGRenderer()

        # render instance question to image format svg
        question_svg = ""
        question_svg = svg_reanderer.renderReactionToBuffer(instance_full_reaction, layout=False)
        question_svg = update_svg_size(question_svg, '100%', '-1') # update svg size to width to 100%

        # get the correct_choices
        correct_choices = []
        for index in range(0,  len(instance_choices)):
            if instance_choices[index][1]:
                correct_choices.append(str(index))

        for instance_choice in instance_choices:
            instance_choice[1] = False

        for answer_index in answer:
            if answer_index != '':
                instance_choices[int(answer_index)][1] = True

        # check if the answer privided are correct or incorrect
        # Get the count of how many quiz histories there are.
        quiz_history_count = DBSession.query(Quiz_history).filter( Quiz_history.user == currentuser.id).filter(Quiz_history.course == course.id).filter(Quiz_history.chapter == chapter.id).count()
        quiz_history_count = quiz_history_count + 1

        if set(answer) != set(correct_choices):
            # record the answer to Quiz_history
            message = "Incorrect"
            result = False
            DBSession.add(Quiz_history( question_number = quiz_history_count, course = course.id, chapter = chapter.id, user = currentuser.id, score=0, reaction_name = custom_reaction.title, quiz_type=reaction_type, reaction_obj = instance_full_reaction, choice_obj = instance_choices ))
        else:
            # record the answer to Quiz_history
            message = "Correct"
            result = True
            DBSession.add(Quiz_history( question_number = quiz_history_count, course = course.id,  chapter = chapter.id, user = currentuser.id, score=1, reaction_name = custom_reaction.title, quiz_type=reaction_type, reaction_obj = instance_full_reaction, choice_obj = instance_choices))

        # Draw the molecules
        for mol in instance_choices:
            mol_choice_svg = svg_reanderer.renderMoleculeToBuffer(mol[0], layout=False )
            # Chop off the xml tag
            mol_choice_svg = mol_choice_svg[mol_choice_svg.find('\n') + 1:]
            # Modify height and width of the svg tag
            svgline = mol_choice_svg[:mol_choice_svg.find('\n')]
            svglineparts = re.split('height=".*?"', svgline)
            svgline = svglineparts[0] + 'height="100%" "' + svglineparts[1]
            svglineparts = re.split('width=".*?"', svgline)
            svgline = svglineparts[0] + 'width="100%" "' + svglineparts[1]
            mol_choice_svg = svgline + "\n" + mol_choice_svg[mol_choice_svg.find('\n') + 1 :]
            mol_choices_svg.append([mol_choice_svg, mol[1] ])    # indicate that these are wrong answers


        # remove the generated question from the Generated_question table
        DBSession.query(Generated_question).filter(Generated_question.id == generated_question.id).delete()

    # elif a current_user has a genereated question then ask the question again.
    elif generated_question is not None:

        # update state to ask user the question
        state = 'ask'

        custom_reaction = DBSession.query(Customizable_reaction).filter(Customizable_reaction.chapter == chapter.id ).filter(Customizable_reaction.reaction == generated_question.reaction ).first()

        # Get it's full reaction name
        page_title = custom_reaction.title

        instance_full_reaction = generated_question.full_reaction # get the full reaction that has been generated

        instance_choices = generated_question.choices # get the multiple choices generated

        # Remove the reactant with a question mark to display as the question
        instance_question = copy.deepcopy(instance_full_reaction)
        molecule = chem.Molecule()
        molecule.addAtom(chem.Atom("?", 0, 0, 0, 0, 0))
        instance_full_reaction.products = [molecule]

        # Initialize draw SVGRenderer object
        svg_reanderer = draw.SVGRenderer()

        # render instance question to image format svg
        question_svg = ""
        question_svg = svg_reanderer.renderReactionToBuffer(instance_full_reaction, layout=False)
        question_svg = update_svg_size(question_svg, '100%', '-1') # update svg size to width to 100%

        # render the instance_choices to image format svg
        choices_svg = []

        for index in range(0,  len(instance_choices)):
            svg = svg_reanderer.renderMoleculeToBuffer(instance_choices[index][0], layout=False)
            svg = update_svg_size(svg, '100%', '100%') # update svg size to height and width to 100%
            choices_svg.append([svg, instance_choices[index][1]])    # indicate that these are correct answers

    return {
            "layout": logged_layout(),
            "custom_scripts" : custom_scripts,
            "page_title" : page_title,
            "basename" : basename,
            "message" : message,
            "result" : result,
            "is_admin" : group["is_admin"], "is_teacher" : group["is_teacher"], "is_student" : group["is_student"],
            "state" : state,
            "owner_courses" : owner_courses,
            "enrolled_courses" : enrolled_courses,
            "logged_in" : request.authenticated_userid,
            "choices_svg" : choices_svg,
            "question_svg" : question_svg,
            "reaction_svg" : reaction_svg,
            "mol_choices_svg" : mol_choices_svg,
        }


@view_config(route_name='quiz_question', renderer='ltefserver:templates/new/quiz_question.pt', permission='study')
def quiz_question_view(request):

    course_name = request.matchdict["course"]
    student_username = request.matchdict["student"]
    quiz_type = request.matchdict["quiz"]
    chapter_name = request.matchdict["chapter"]
    is_incorrect = False
    is_correct = False
    message = ""
    custom_scripts =[]

    current_user = DBSession.query(User).filter(User.username == request.authenticated_userid).first()
    group = group_security(request.authenticated_userid)

    owner_courses = []
    enrolled_courses = []
    if group["is_teacher"]:
        owner_courses = Course.owner_courses(request.authenticated_userid)
        course = DBSession.query(Course).filter(Course.name == course_name).filter(Course.owner == current_user.id).first()
        student = DBSession.query(User).filter(User.username == student_username).first()
        chapter = DBSession.query(Chapter).filter(Chapter.title == chapter_name).filter(Chapter.course == course.id).first()

        quiz = DBSession.query(Quiz_history).filter(Quiz_history.user== student.id).filter(Quiz_history.course == course.id).filter(Quiz_history.chapter == chapter.id).filter(Quiz_history.question_number == quiz_type).first()
    elif group["is_student"]:
        enrolled_courses = Enrolled.enrolled_courses(request.authenticated_userid)
	course = DBSession.query(Course).filter(Course.name == course_name).filter(Course.id == Enrolled.courseid).filter(Enrolled.userid == current_user.id).first()
        student = DBSession.query(User).filter(User.username == student_username).first()
        chapter = DBSession.query(Chapter).filter(Chapter.title == chapter_name).filter(Chapter.course == course.id).first()
        quiz = DBSession.query(Quiz_history).filter(Quiz_history.user== current_user.id).filter(Quiz_history.course == course.id).filter(Quiz_history.chapter == chapter.id).filter(Quiz_history.question_number == quiz_type).first()

    choices = quiz.choice_obj

    if quiz.score == 0:
        message = "You have selected the incorrect answer"
        is_incorrect = True
    elif quiz.score == 1:
        message = "You have selected the correct Answer"
        is_correct = True


    # Draw the reaction in svg
    instance = quiz.reaction_obj
    render_draw = draw.SVGRenderer()
    reaction_svg = render_draw.renderReactionToBuffer(instance, layout=False)

    # Chop off the xml tag
    reaction_svg = reaction_svg[reaction_svg.find('\n') + 1:]
    # Modify height and width of the svg tag
    svgline = reaction_svg[:reaction_svg.find('\n')]
    svglineparts = re.split('width=".*?"', svgline)
    svgline = svglineparts[0] + 'width="100%"' + svglineparts[1]
    reaction_svg = svgline + "\n" + reaction_svg[reaction_svg.find('\n') + 1 :]


    molecule = chem.Molecule()
    molecule.addAtom(chem.Atom("?", 0, 0, 0, 0, 0))
    if quiz.quiz_type == 'reactants':
        instance.reactants = [molecule]
    elif quiz.quiz_type == 'products':
        instance.products = [molecule]

    question_svg = render_draw.renderReactionToBuffer(instance, layout=False)

    # Chop off the xml tag
    question_svg = question_svg[question_svg.find('\n') + 1:]
    # Modify height and width of the svg tag
    svgline = question_svg[:question_svg.find('\n')]
    svglineparts = re.split('width=".*?"', svgline)
    svgline = svglineparts[0] + 'width="100%"' + svglineparts[1]
    question_svg = svgline + "\n" + question_svg[question_svg.find('\n') + 1 :]

    # Draw the molecules
    mol_choices_svg = []
    for mol in choices:
	mol_choice_svg = render_draw.renderMoleculeToBuffer(mol[0], layout=False )
	    # Chop off the xml tag
        mol_choice_svg = mol_choice_svg[mol_choice_svg.find('\n') + 1:]
        # Modify height and width of the svg tag
        svgline = mol_choice_svg[:mol_choice_svg.find('\n')]
        svglineparts = re.split('height=".*?"', svgline)
        svgline = svglineparts[0] + 'height="100%" "' + svglineparts[1]
        svglineparts = re.split('width=".*?"', svgline)
        svgline = svglineparts[0] + 'width="100%" "' + svglineparts[1]
        mol_choice_svg = svgline + "\n" + mol_choice_svg[mol_choice_svg.find('\n') + 1 :]
	mol_choices_svg.append([mol_choice_svg, mol[1] ])    # indicate that these are wrong answers

    return {"layout": logged_layout(),
            "logged_in" : request.authenticated_userid,
            "message" : message,
            "reaction_svg" : reaction_svg,
	    "owner_courses" : owner_courses,
            "enrolled_courses" : enrolled_courses,
	    "custom_scripts" : custom_scripts,
            "is_admin" : group["is_admin"], "is_teacher" : group["is_teacher"], "is_student" : group["is_student"],
            "page_title" : student.firstname.title() + " " + student.lastname.title() + " " + "quiz question #" + str(quiz.question_number),
            "is_correct" : is_correct,
            "is_incorrect" : is_incorrect,
            "question_svg" : question_svg,
	    "mol_choices_svg" : mol_choices_svg,
           }





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
    quiz_histories = DBSession.query(Quiz_history, Chapter, Course, User).filter(Chapter.course == Course.id).filter(User.id == student.id).filter(Quiz_history.user == student.id).filter(Quiz_history.course == course.id).filter(Chapter.id == Quiz_history.chapter).all()

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
            "page_title" : student.firstname + " " + student.lastname + " Quiz History"      }


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


@view_config(route_name='quiz_products', renderer='ltefserver:templates/new/quiz_products.pt', permission='educate')
def quiz_products_view(request):

        # global variable instance reaction stores the whole reaction question
        global instance_reaction
        # globel variable instance choice stores a list of molecule choice questions
        global instance_choices
        # globel variable correct_choices stores a list of the correct choice position
        global correct_choices


        mode = request.matchdict["basename"]
        reaction_type = "products"
        currentuser = User.current_user(request.authenticated_userid)
        custom_scripts = []
        custom_scripts.append("/bootstrap/js/quiz_reactants.js")

        # Get the users security group
        group = group_security(request.authenticated_userid)

        session = request.session
        basename = ""
        full_name = ""
        message = ""

        # Two type of states Ask the question or Tell if answer by result being correct or incorrect
        state = "ask"
        result = False

        global question_svg
        global reaction_svg
        global product_svgs

        # Generate a problem, store the objects, present to user
        if ('quiz_type' not in session or session['quiz_type'] != 'products' or question_svg == "")  and  "answer" not in request.GET :

            session.invalidate()
            session['quiz_type'] = 'products'
            state = "ask"


            # if mode is random select a reaction randomly
            if mode == "random":
                basename = random.choice(cat.get_sorted_basenames())
            else:
                basename = mode

            # retrieve the raction
            reaction = cat.get_reaction_by_basename(basename)
            # Get it's full reaction name
            full_name = reaction.full_name

            # prepare instance, cut off reactants
            instance = reaction.getInstance()
            instance_reaction = copy.deepcopy(instance)
            reactants = instance.reactants
            products = instance.products

            # Initialize draw SVGRenderer object
            svg_reanderer = draw.SVGRenderer()
            # Draw the full image of the reaction
            reaction_svg = ""
            reaction_svg = svg_reanderer.renderReactionToBuffer(instance, layout=False)

            # Hide the reactant from the Question and add a question mark
            molecule = chem.Molecule()
            molecule.addAtom(chem.Atom("?", 0, 0, 0, 0, 0))
            instance.products = [molecule]

            # Reaction image without reactants
            question_svg = ""
            question_svg = svg_reanderer.renderReactionToBuffer(instance, layout=False)

            # Chop off the xml tag
            question_svg = question_svg[question_svg.find('\n') + 1:]
            # Modify height and width of the svg tag
            svgline = question_svg[:question_svg.find('\n')]
            svglineparts = re.split('width=".*?"', svgline)
            svgline = svglineparts[0] + 'width="100%"' + svglineparts[1]
            question_svg = svgline + "\n" + question_svg[question_svg.find('\n') + 1 :]

            product_svgs = []
            instance_choices = []

            # Add all the correct choices to instance_choices
            for molecule in products:
                instance_choices.append([molecule, True])

            # Initializes object bastardReaction to generate wrong answers
            distractor_reaction = distractor.DistractorReaction(reactants, products)

            # Add all the incorrect choices to instance_choices
            for molecule in distractor_reaction.generate_product_distractors():
                instance_choices.append([molecule, False])

            # shuffle the molecule choices
            random.shuffle(instance_choices)

            correct_choices = []
            # Draw the molecule choices and store the correct choices in a global set correct_choices
            for index in range(0,  len(instance_choices)):
                svg =  svg_reanderer.renderMoleculeToBuffer(instance_choices[index][0], layout=False)
                # Chop off the xml tag
                svg = svg[svg.find('\n') + 1:]
                # Modify height and width of the svg tag
                svgline = svg[:svg.find('\n')]
                svglineparts = re.split('height=".*?"', svgline)
                svgline = svglineparts[0] + 'height="100%" "' + svglineparts[1]
                svglineparts = re.split('width=".*?"', svgline)
                svgline = svglineparts[0] + 'width="100%"' + svglineparts[1]
                svg = svgline + "\n" + svg[svg.find('\n') + 1 :]

                product_svgs.append([svg, instance_choices[index][1]])    # indicate that these are correct answers
                if instance_choices[index][1]:
                    correct_choices.append(str(index))

            session['basename'] = basename
            print "Started a quiz (products) session for " + basename

        # Depending on request parameters, either
        #   - continue session, or
        #   - present the answer to problem and a show a button to get a new problem
        else:
            basename = session['basename']
            quiz_type = session['quiz_type']
            #print "Resuming a quiz (products) session for " + basename
            reaction = cat.get_reaction_by_basename(basename)
            full_name = reaction.full_name
            answer = []
            if "answer" in request.GET:

                answer = request.GET["answer"].split(",")

                # Invalidate the session
                state = "tell"
                session.invalidate()
                question_svg = ""

    	    for instance_choice in instance_choices:
    		instance_choice[1] = False

    	    for answer_index in answer:
                if answer_index != '':
                    instance_choices[int(answer_index)][1] = True

                if set(answer) != set(correct_choices):
                    message = "Wrong!"
                    result = False

                else:
                    message = "Correct! You selected what's necessary and nothing else."
                    result = True

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
                "message" : message,
                "result" : result,
                "is_admin" : group["is_admin"], "is_teacher" : group["is_teacher"], "is_student" : group["is_student"],
                "state" : state,
                "owner_courses" : owner_courses,
                "enrolled_courses" : enrolled_courses,
                "logged_in" : request.authenticated_userid,
                "reaction_svg" : reaction_svg,
                "question_svg" : question_svg,
                "product_svgs" : product_svgs,

            }



@view_config(route_name='quiz_reactants', renderer='ltefserver:templates/new/quiz_reactants.pt', permission='study')
def quiz_reactants_view(request):

    # global variable instance reaction stores the whole reaction question
    global instance_reaction
    # globel variable instance choice stores a list of molecule choice questions
    global instance_choices
    # globel variable correct_choices stores a list of the correct choice position
    global correct_choices


    mode = request.matchdict["basename"]
    reaction_type = "reactants"
    currentuser = User.current_user(request.authenticated_userid)
    custom_scripts = []
    custom_scripts.append("/bootstrap/js/quiz_reactants.js")

    # Get the users security group
    group = group_security(request.authenticated_userid)

    session = request.session
    basename = ""
    full_name = ""
    message = ""

    # Two type of states Ask the question or Tell if answer by result being correct or incorrect
    state = "ask"
    result = False

    global question_svg
    global reaction_svg
    global reactant_svgs

    # Generate a problem, store the objects, present to user
    if ('quiz_type' not in session or session['quiz_type'] != 'reactants' or question_svg == "") and  "answer" not in request.GET:

        session.invalidate()
        session['quiz_type'] = 'reactants'
        state = "ask"


        # if mode is random select a reaction randomly
        if mode == "random":
            basename = random.choice(cat.get_sorted_basenames())
        else:
            basename = mode

        # retrieve the raction
        reaction = cat.get_reaction_by_basename(basename)
        # Get it's full reaction name
        full_name = reaction.full_name

        # prepare instance, cut off reactants
        instance = reaction.getInstance()
        instance_reaction = copy.deepcopy(instance)
        reactants = instance.reactants
        products = instance.products

        # Initialize draw SVGRenderer object
        svg_reanderer = draw.SVGRenderer()
        # Draw the full image of the reaction
        reaction_svg = ""
        reaction_svg = svg_reanderer.renderReactionToBuffer(instance, layout=False)

        # Hide the reactant from the Question and add a question mark
        molecule = chem.Molecule()
        molecule.addAtom(chem.Atom("?", 0, 0, 0, 0, 0))
        instance.reactants = [molecule]

        # Reaction image without reactants
        question_svg = ""
        question_svg = svg_reanderer.renderReactionToBuffer(instance, layout=False)

        # Chop off the xml tag
        question_svg = question_svg[question_svg.find('\n') + 1:]
        # Modify height and width of the svg tag
        svgline = question_svg[:question_svg.find('\n')]
        svglineparts = re.split('width=".*?"', svgline)
        svgline = svglineparts[0] + 'width="100%"' + svglineparts[1]
        question_svg = svgline + "\n" + question_svg[question_svg.find('\n') + 1 :]

        reactant_svgs = []
        instance_choices = []

        # Add all the correct choices to instance_choices
        for molecule in reactants:
            instance_choices.append([molecule, True])

        # Initializes object bastardReaction to generate wrong answers
        distractor_reaction = distractor.DistractorReaction(reactants, products)

        # Add all the incorrect choices to instance_choices
        for molecule in distractor_reaction.generate_reactant_distractors():
            instance_choices.append([molecule, False])

        # shuffle the molecule choices
        random.shuffle(instance_choices)

        correct_choices = []
        # Draw the molecule choices and store the correct choices in a global set correct_choices
        for index in range(0,  len(instance_choices)):
            svg =  svg_reanderer.renderMoleculeToBuffer(instance_choices[index][0], layout=False)
            # Chop off the xml tag
            svg = svg[svg.find('\n') + 1:]
            # Modify height and width of the svg tag
            svgline = svg[:svg.find('\n')]
            svglineparts = re.split('height=".*?"', svgline)
            svgline = svglineparts[0] + 'height="100%" "' + svglineparts[1]
            svglineparts = re.split('width=".*?"', svgline)
            svgline = svglineparts[0] + 'width="100%"' + svglineparts[1]
            svg = svgline + "\n" + svg[svg.find('\n') + 1 :]

            reactant_svgs.append([svg, instance_choices[index][1]])    # indicate that these are correct answers
            if instance_choices[index][1]:
                correct_choices.append(str(index))

        session['basename'] = basename
        print "Started a quiz (reactants) session for " + basename

    # Depending on request parameters, either
    #   - continue session, or
    #   - present the answer to problem and a show a button to get a new problem
    else:
        basename = session['basename']
        quiz_type = session['quiz_type']
        reaction = cat.get_reaction_by_basename(basename)
        full_name = reaction.full_name

        answer = []
        if "answer" in request.GET:
            answer = request.GET["answer"].split(",")

            # Invalidate the session
            state = "tell"
            session.invalidate()
            question_svg = ""

	    for instance_choice in instance_choices:
		instance_choice[1] = False

        for answer_index in answer:
            if answer_index != '':
                instance_choices[int(answer_index)][1] = True

            if set(answer) != set(correct_choices):
                message = "Wrong!"
                result = False
            else:
                message = "Correct! You selected what's necessary and nothing else."
                result = True

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
            "message" : message,
            "result" : result,
            "is_admin" : group["is_admin"], "is_teacher" : group["is_teacher"], "is_student" : group["is_student"],
            "state" : state,
            "owner_courses" : owner_courses,
            "enrolled_courses" : enrolled_courses,
            "logged_in" : request.authenticated_userid,
            "reaction_svg" : reaction_svg,
            "question_svg" : question_svg,
            "reactant_svgs" : reactant_svgs,
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
