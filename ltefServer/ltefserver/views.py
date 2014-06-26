from pyramid.view import view_config
from pyramid.renderers import get_renderer
from pyramid.response import FileResponse, Response
from pyramid.httpexceptions import HTTPNotFound

import os
import sys
sys.path.append('../python')
sys.path.append('./indigo-python-1.1.12')
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
    #print "A request for learning page - list of reactions"
    return {"layout" : site_layout(), "reactions" : catalog.get_reaction_names_sorted()}

@view_config(route_name='learning_reaction', renderer='templates/learning_reaction.pt')
def learning_reaction_view(request):
    #print "A request for examples page for reaction " + request.matchdict["basename"]
    basename = request.matchdict["basename"]
    #print "Got basename"
    full_name = catalog.get_reaction_dict()[basename]
    path = os.path.join(catalog.get_path_to_rxn(), basename + ".rxn")
    reaction = rxn.parse_rxn(path)
    #print "Got full name: " + full_name
    desc = catalog.get_reaction_description(basename)
    #print "Got description: " + desc
    return {"layout" : site_layout(), "basename" : basename, "full_name" : full_name, "reaction_description" : desc, "rgroups" : reaction.rgroups}

@view_config(route_name='img')
def img_view(request):
    param_str = request.matchdict["filename"]
    mode = request.matchdict["what"]
    path = os.path.join(catalog.get_path_to_rxn(), request.matchdict["basename"] + ".rxn")
    reaction = rxn.parse_rxn(path)
    response = HTTPNotFound()

    if mode == "generic":
        response = Response(content_type='image/png', body=draw.renderReactionToBuffer(reaction).tostring())
    elif mode == "instance":
        instance = reaction.getInstance()
        response = Response(content_type='image/png', body=draw.renderReactionToBuffer(instance).tostring())
    elif mode == "rgroup":
        params = param_str.split(",")
        # first arg is "R1", "R2", etc.
        # second arg is the list index of specific molecule which the group could be
        # e.g. "...?R1,0" is for the first choice of R1
        if len(params) == 2:
            buf = draw.renderRGroupToBuffer(reaction, params[0].upper(), int(params[1]))
            if buf is not None:
                response = Response(content_type='image/png', body=buf.tostring())

    return response