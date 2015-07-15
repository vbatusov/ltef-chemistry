""" Module for drawing molecules and reactions.
"""

import chem
import sys
#sys.path.append('../ltefServer/indigo-python-1.2.1-linux/')
from indigo import *
from indigo_renderer import *

def get_indigo():
    indigo = Indigo()
    renderer = IndigoRenderer(indigo)
    indigo.setOption("render-output-format", "png")
    indigo.setOption("render-margins", 10, 10)
    indigo.setOption("render-coloring", True)
    indigo.setOption("render-bond-length",50)
    indigo.setOption("render-atom-ids-visible", False)
    #indigo.setOption("render-aam-color", 0.5, 0.5, 1.0)

    return (indigo, renderer)

def add_actors_to_ireaction(indigo, actors, func, layout=True):
    aam_to_iatom = {}
    for mol in actors:
        imol = indigo.createMolecule()
        for atom in mol.atomList:
            iatom = None
            if atom.symbol[0]=="R":
                iatom = imol.addRSite(atom.symbol)
            else:
                iatom = imol.addAtom(atom.symbol)
            # Set charge if there is one
            if "CHG" in atom.attribs.keys():
                iatom.setCharge(int(atom.attribs["CHG"]))
            # Set original RXN XYZ coordinates
            iatom.setXYZ(atom.x, atom.y, atom.z)

            aam_to_iatom[atom.aam] = iatom
        for bond in mol.bondList:
            iatom1 = aam_to_iatom[bond.fromAtom.aam]
            iatom2 = aam_to_iatom[bond.toAtom.aam]
            ibond = iatom1.addBond(iatom2, bond.order)
        if layout:
            imol.layout()

        # Add indigo molecule to indigo reaction
        # This, unfortunately, copies the molecule to reaction object and returns 1 on success.
        # No standard way to get a reference to that copy to set the mapping numbers.
        func(imol)


def renderReactionToBuffer(reaction, highlight=False, layout=True):
    (indigo, renderer) = get_indigo()
    indigo.setOption("render-image-size", 940, -1)
    # First, re-create the reaction as an Indigo object
    ireaction = indigo.createReaction()

    add_actors_to_ireaction(indigo, reaction.reactants, ireaction.addReactant, layout)
    add_actors_to_ireaction(indigo, reaction.agents, ireaction.addCatalyst, layout)
    add_actors_to_ireaction(indigo, reaction.products, ireaction.addProduct, layout)

    # Hide hydrogens - experiment
    ireaction.foldHydrogens()

    if highlight:
        indigo.setOption("render-background-color", 1.0, 0.9, 0.8)

    buf = renderer.renderToBuffer(ireaction)

    if highlight:
        indigo.setOption("render-background-color", 1.0, 0.9, 0.8)

    return buf

# This is a dumb copy with a minor edit, rethink this!!
def renderReactionToBufferSVG(reaction, highlight=False, layout=True):
    (indigo, renderer) = get_indigo()
    indigo.setOption("render-image-size", 800, -1)  # isn't this irrelevant for svg?
    indigo.setOption("render-output-format", "svg")
    # First, re-create the reaction as an Indigo object
    ireaction = indigo.createReaction()

    add_actors_to_ireaction(indigo, reaction.reactants, ireaction.addReactant, layout)
    add_actors_to_ireaction(indigo, reaction.agents, ireaction.addCatalyst, layout)
    add_actors_to_ireaction(indigo, reaction.products, ireaction.addProduct, layout)

    # Hide hydrogens - experiment
    ireaction.foldHydrogens()

    if highlight:
        indigo.setOption("render-background-color", 1.0, 0.9, 0.8)

    buf = renderer.renderToBuffer(ireaction)

    if highlight:
        indigo.setOption("render-background-color", 1.0, 0.9, 0.8)

    return buf

def renderMoleculeToBuffer(mol, highlight=False):
    print str(highlight)
    (indigo, renderer) = get_indigo()
    indigo.setOption("render-image-size", 220, 119)

    aam_to_iatom = {}
    imol = indigo.createMolecule()
    for atom in mol.atomList:
        iatom = None
        if atom.symbol[0]=="R":
            iatom = imol.addRSite(atom.symbol)
        else:
            iatom = imol.addAtom(atom.symbol)
        # Set charge if there is one
        if "CHG" in atom.attribs.keys():
            iatom.setCharge(int(atom.attribs["CHG"]))
        aam_to_iatom[atom.aam] = iatom
    for bond in mol.bondList:
         iatom1 = aam_to_iatom[bond.fromAtom.aam]
         iatom2 = aam_to_iatom[bond.toAtom.aam]
         ibond = iatom1.addBond(iatom2, bond.order)
    imol.layout()

    # Hide hydrogens - experiment
    imol.foldHydrogens()

    if highlight:
        print "\n\n* * * MODIFYING RENDERER * * *\n\n"
        indigo.setOption("render-background-color", 1.0, 0.9, 0.8)
    else:
        print "\n\n* * * NOT MODIFYING RENDERER * * *\n\n"

    buf = renderer.renderToBuffer(imol)

    if highlight:
        indigo.setOption("render-background-color", 1.0, 0.9, 0.8)

    return buf

def renderRGroupToBuffer(reaction, rname, nmol):
    (indigo, renderer) = get_indigo()

    if rname not in reaction.rgroups.keys() or nmol >= len(reaction.rgroups[rname]):
        return None

    mol = reaction.rgroups[rname][nmol]

    aam_to_iatom = {}
    imol = indigo.createMolecule()
    for atom in mol.atomList:
        iatom = imol.addAtom(atom.symbol)
        # Show that anchor is connected to molecule
        if mol.anchor == atom:
            #ref = imol.addAtom("*")
            #ref.addBond(iatom, 1)
            iatom.highlight()
        # Set charge if there is one
        if "CHG" in atom.attribs.keys():
            iatom.setCharge(int(atom.attribs["CHG"]))
        aam_to_iatom[atom.aam] = iatom
    for bond in mol.bondList:
         iatom1 = aam_to_iatom[bond.fromAtom.aam]
         iatom2 = aam_to_iatom[bond.toAtom.aam]
         ibond = iatom1.addBond(iatom2, bond.order)
    imol.layout()

    buf = renderer.renderToBuffer(imol)

    return buf
