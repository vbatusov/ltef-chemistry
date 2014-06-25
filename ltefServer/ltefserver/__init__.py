from pyramid.config import Configurator

#from pyramid.httpexceptions import HTTPUnauthorized
from pyramid.response import Response

#def myviewfunction(request):
#    return HTTPUnauthorized()

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    config.include('pyramid_chameleon')
    config.add_static_view('static', 'static', cache_max_age=3600)

    config.add_route('home', '/')
    config.add_route('tools', '/tools')
    config.add_route('synthesis', '/tools/synthesis')
    config.add_route('learning', '/tools/learning')
    config.add_route('learning_reaction', '/tools/learning/{basename}')
    config.add_route('pic_generic', '/img/generic_{basename}.png')
    config.add_route('pic_instance', '/img/instance_{basename}.png')
    config.add_route('pic_rgroup', '/img/rgroup_{basename}.{params}.png')
    config.scan()
    return config.make_wsgi_app()
