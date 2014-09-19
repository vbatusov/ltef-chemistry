""" Module for drawing molecules and reactions.
"""

import chem
import sys
sys.path.append('../ltefServer/indigo-python-1.1.12/')
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

def add_actors_to_ireaction(indigo, actors, func):
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
            aam_to_iatom[atom.aam] = iatom 
        for bond in mol.bondList:
            iatom1 = aam_to_iatom[bond.fromAtom.aam]
            iatom2 = aam_to_iatom[bond.toAtom.aam]
            ibond = iatom1.addBond(iatom2, bond.order)
        imol.layout()

        # Add indigo molecule to indigo reaction
        # This, unfortunately, copies the molecule to reaction object and returns 1 on success.
        # No standard way to get a reference to that copy to set the mapping numbers.
        func(imol)


def renderReactionToBuffer(reaction):
    (indigo, renderer) = get_indigo()
    indigo.setOption("render-image-size", 940, -1)
    # First, re-create the reaction as an Indigo object
    ireaction = indigo.createReaction()

    add_actors_to_ireaction(indigo, reaction.reactants, ireaction.addReactant)
    add_actors_to_ireaction(indigo, reaction.agents, ireaction.addCatalyst)
    add_actors_to_ireaction(indigo, reaction.products, ireaction.addProduct)

    # Hide hydrogens - experiment
    ireaction.foldHydrogens()

    buf = renderer.renderToBuffer(ireaction)

    return buf

def renderMoleculeToBuffer(mol):
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

    buf = renderer.renderToBuffer(imol)

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



# folder = 'img'
# for the_file in os.listdir(folder):
#     file_path = os.path.join(folder, the_file)
#     try:
#         if os.path.isfile(file_path):
#             os.unlink(file_path)
#     except Exception, e:
#         print e

# indigo = Indigo()
# renderer = IndigoRenderer(indigo)
# outputFormat = "png"
# indigo.setOption("render-output-format", outputFormat)
# indigo.setOption("render-margins", 10, 10)
# indigo.setOption("render-coloring", True)
# indigo.setOption("render-bond-length",50)
# indigo.setOption("render-atom-ids-visible", False)
# indigo.setOption("render-aam-color", 0.5, 0.5, 1.0)

# reaction = parse_rxn("amide.rxn")
# print "\n" + str(reaction)

# print "\n.........   Instance   ............"

# reactionInst = reaction.getInstance()
# print "\n" + str(reactionInst)

# for reactant in reactionInst.reactants:
#     indo = reactant.getIndigoObject(indigo)
#     smiles = indo.canonicalSmiles()
#     #print "Created new " + str(molecule) + " with SMILES " + smiles
#     safename = base64.urlsafe_b64encode(smiles)
#     indo.layout()
#     renderer.renderToFile(indo, "img/reactant-" + safename + ".png");
#     print " -> Written the molecule image to " + safename + ".png"

# for product in reactionInst.products:
#     indo = product.getIndigoObject(indigo)
#     smiles = indo.canonicalSmiles()
#     #print "Created new " + str(molecule) + " with SMILES " + smiles
#     safename = base64.urlsafe_b64encode(smiles)
#     indo.layout()
#     renderer.renderToFile(indo, "img/product-" + safename + ".png");
#     print " -> Written the molecule image to " + safename + ".png"

    # from Molecule
    # def getIndigoObject(self, indigo):
    #     indigo_mol = indigo.createMolecule()
    #     indigo_atoms = {}
    #     for atom in self.atomList:
    #         indigo_atoms[atom.aam] = indigo_mol.addAtom(atom.symbol)
    #         print "Added indigo atom " + indigo_atoms[atom.aam].symbol()
    #     for bond in self.bondList:
    #         indigo_atoms[bond.fromAtom.aam].addBond(indigo_atoms[bond.toAtom.aam], bond.order)

    #     return indigo_mol




    # # DEBUG render the molecule; this tests both structure and indigo interaction
    # indigo_molecule = molecule.getIndigoObject(indigo)
    # smiles = indigo_molecule.canonicalSmiles()
    # #print "Created new " + str(molecule) + " with SMILES " + smiles
    # safename = base64.urlsafe_b64encode(smiles)
    # indigo_molecule.layout()
    # renderer.renderToFile(indigo_molecule, "img/raw-" + safename + ".png");
    # print " -> Written the molecule image to " + safename + ".png"
