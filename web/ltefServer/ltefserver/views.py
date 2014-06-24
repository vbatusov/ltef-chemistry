from pyramid.view import view_config
from pyramid.renderers import get_renderer
from pyramid.response import FileResponse, Response

import os
import sys
sys.path.append('/home/vitaliy/ltef_project/ltef-chemistry/python')
import rxn
import chem
import draw
import catalog


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

@view_config(route_name='synthesis', renderer='templates/synthesis.pt')
def synthesis_view(request):
    return {"layout": site_layout()}

@view_config(route_name='learning', renderer='templates/learning.pt')
def learning_view(request):
    print "A request for learning page - list of reactions"
    return {"layout" : site_layout(), "reactions" : catalog.get_reaction_names_sorted()}

@view_config(route_name='learning_reaction', renderer='templates/learning_reaction.pt')
def learning_reaction_view(request):
    print "A request for examples page for reaction " + request.matchdict["basename"]
    basename = request.matchdict["basename"]
    print "Got basename"
    full_name = catalog.get_reaction_dict()[basename]
    print "Got full name: " + full_name
    desc = catalog.get_reaction_description(basename)
    print "Got description: " + desc
    return {"layout" : site_layout(), "basename" : basename, "full_name" : full_name, "reaction_description" : desc}

@view_config(route_name='pic_generic')
def pic_generic_view(request):
    print "A request for a picture of a generic reaction"
    path = os.path.join(catalog.get_path_to_rxn(), request.matchdict["basename"] + ".rxn")
    print "Will parse file " + path
    reaction = rxn.parse_rxn(path)
    print "Parsed successfully, rendering to picture"
    buf = draw.renderReactionToBuffer(reaction)
    print "Picture ready for generic " + path
    return Response(content_type='image/png', body=buf.tostring())

@view_config(route_name='pic_instance')
def pic_instance_view(request):
    print "A request for a picture of a specific reaction"
    path = os.path.join(catalog.get_path_to_rxn(), request.matchdict["basename"] + ".rxn")
    print "Will parse file " + path
    reaction = rxn.parse_rxn(path)
    print "Parsed successfully, getting an instance"
    instance = reaction.getInstance()
    print "Computed instance, rendering to picture"
    buf = draw.renderReactionToBuffer(instance)
    print "Picture ready for instance " + path
    return Response(content_type='image/png', body=buf.tostring())
