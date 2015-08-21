# Basics
from pyramid.config import Configurator
from pyramid.response import Response

# Sessions
from pyramid.session import SignedCookieSessionFactory

# DB
from sqlalchemy import engine_from_config
from .models import (DBSession, Base)

# Authorization
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from ltefserver.security import groupfinder



def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    # Set up DB
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine

    # Set up Auth
    authn_policy = AuthTktAuthenticationPolicy('sosecret', callback=groupfinder, hashalg='sha512')
    authz_policy = ACLAuthorizationPolicy()

    # Create config
    config = Configurator(settings=settings, root_factory='ltefserver.models.RootFactory')
    config.set_authentication_policy(authn_policy)
    config.set_authorization_policy(authz_policy)

    # Set up sessions
    my_session_factory = SignedCookieSessionFactory('itsaseekreet')
    config.set_session_factory(my_session_factory)

    config.include('pyramid_chameleon')
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_static_view('bootstrap', 'bootstrap', cache_max_age=3600)


    config.add_route('login', '/login')

    config.add_route('logout', '/logout')
    config.add_route('password_reset', '/password_reset')
    config.add_route('security_question', '/password_reset/security_question')
    config.add_route('reset_password', '/reset_password')
    config.add_route('student_register', '/student_register')
    config.add_route('add_course', '/add_course')

    #User must add a secret question to be able to reset password
    config.add_route('add_secret_question', '/add_secret_question')

    config.add_route('select_register', '/select_register')
    config.add_route('select_quiz', '/select_quiz')
    # Route to teacher's course creation page
    config.add_route('createcourse', '/tools/createcourse')
    # Route to student's course sign up page
    config.add_route('course_signup', '/tools/course_signup')

    config.add_route('home', '/')
    config.add_route('synthesis', '/tools/synthesis')
    config.add_route('addreaction', '/tools/addreaction')
    config.add_route('about', '/about')
    config.add_route('contact', '/contact')
    config.add_route('learning', '/tools/learning')
    config.add_route('learning_reaction', '/tools/learning/{basename}')
    config.add_route('img', '/img/{basename}/{what}/{filename}.png')
    config.add_route('img_by_id', '/img/q_{id}/{which}.png')
    config.add_route('img_from_history', '/img/h_{id}/{which}.png')
    config.add_route('quiz_reactants', '/tools/quiz/reactants/{basename}')
    config.add_route('quiz_products', '/tools/quiz/products/{basename}')
    config.add_route('quiz_reaction', '/tools/quiz/reaction')
    config.add_route('quiz_history', '/tools/quiz/history')

    config.add_route('manageusers', '/manageusers')
    config.add_route('managelists', '/tools/managelists')
    config.add_route('editlist', '/tools/managelists/edit')


    # Course
    config.add_route('class', '/class/{basename}')

    # Course action
    config.add_route('class_action', '/class/{basename}/{action}')

    # Student Quiz history
    config.add_route('student_quiz_history', '/class/{course}/{student}/quiz_history')

    # Student actions i.e. remove_student
    config.add_route('remove_student', '/class/{course}/{student}/remove_student')

    # Chapter action
    config.add_route('chapter_action', '/class/{basename}/{chapter}/{action}')

    # Edit Account
    config.add_route('edit_account', '/edit_account')

    # Chapter reaction
    config.add_route('learn_by_example_reaction','/class/{basename}/{chapter}/learn_by_example/{reaction}')
    config.add_route('quiz','/class/{course}/{chapter}/quiz/{quiz_type}/{basename}')
    # Quiz
    config.add_route('select_reaction_quiz', '/class/{course}/{chapter}/select_reaction_quiz/{basename}')


    config.scan()

    return config.make_wsgi_app()
