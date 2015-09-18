"""
Module for drawing molecules and reactions.
"""

import chem
import sys
from indigo import *
from indigo_renderer import *

def get_indigo():
    """ Creates an Indigo object. According to authors, this is a cheap operation. """

    indigo = Indigo()
    renderer = IndigoRenderer(indigo)
    indigo.setOption("render-margins", 10, 10)
    indigo.setOption("render-coloring", True)
    indigo.setOption("render-bond-length", 50)
    indigo.setOption("render-atom-ids-visible", False)
    #indigo.setOption("render-aam-color", 0.5, 0.5, 1.0)

    return (indigo, renderer)


def build_indigo_reaction(reaction, indigo, layoutReac=False, layoutAgent=False, layoutProd=False):
    """ Given a chem.Reaction object, creates an equivalent Indigo reaction object. """

    ireaction = indigo.createReaction()

    add_actors_to_ireaction(indigo, reaction.reactants, ireaction.addReactant, layoutReac)
    add_actors_to_ireaction(indigo, reaction.agents, ireaction.addCatalyst, layoutAgent)
    add_actors_to_ireaction(indigo, reaction.products, ireaction.addProduct, layoutProd)

    return ireaction


def build_indigo_molecule(molecule, indigo, layout=False):
    # A map from real AAM to Indigo atom objects. The map is filled as Indigo atoms are created,
    # and is then used to create bonds between Indigo atoms.
    aam_to_iatom = {}

    # A new Indigo molecule
    imol = indigo.createMolecule()

    # Maps each stereocenter Indigo atom index to its stereo configuration.
    # THe configuration is a dictionary with "parity" (value 1 for clockwise, 2 for counterclockwise)
    # and "pyramid" (a list of pairs (<indigo atom index>, <corresponding rxn atom index>) which identify the neighbours
    # of the stereocenter; the rxn atom indeces are necessary for sorting the indigo indeces to correctly express
    # the stereo configuration later on)
    stereocenter_data = {}

    # RXN atom coordinates stored as a map from Indigo atom indeces to triples (x,y,z);
    # this is necessary to preserve spatial arrangement of atoms.
    xyz = {}

    # Construct Indigo atoms
    for atom in molecule.atomList:

        iatom = None

        # Add atom to molecule
        if atom.symbol[0]=="R" and atom.symbol[1].isdigit():
            iatom = imol.addRSite(atom.symbol)
        else:
            iatom = imol.addAtom(atom.symbol)

        # Set charge if there is one
        if "CHG" in atom.attribs.keys():
            iatom.setCharge(int(atom.attribs["CHG"]))

        # Store the original RXN XYZ coordinates
        xyz[iatom.index()] = (atom.x, atom.y, atom.z)

        # If atom is a stereocenter, store its parity and prepare an empty list for the pyramid
        if "CFG" in atom.attribs.keys():
            stereocenter_data[iatom.index()] = { "parity" : int(atom.attribs["CFG"]), "pyramid" : [] }

        # Remember which Indigo atom current aam corresponds to
        aam_to_iatom[atom.aam] = iatom

    # Construct Indigo bonds
    for bond in molecule.bondList:

        # Recover Indigo atoms from aam map and recreate the bond
        iatom1 = aam_to_iatom[bond.fromAtom.aam]
        iatom2 = aam_to_iatom[bond.toAtom.aam]
        ibond = iatom1.addBond(iatom2, bond.order)

        # If the bond has stereo config, cry me a river since Indigo 1.2.1 provides no API to set it.
        if "CFG" in bond.attribs.keys():
            pass

        # If the bond involves a stereocentre, add *the other atom*'s index to stereocenter_data's pyramid
        if iatom1.index() in stereocenter_data:
            stereocenter_data[iatom1.index()]["pyramid"].append((iatom2.index(), bond.toAtom.rxnIndex))
        if iatom2.index() in stereocenter_data:
            stereocenter_data[iatom2.index()]["pyramid"].append((iatom1.index(), bond.fromAtom.rxnIndex))

    # Arrange the pyramid list atom indeces so that their order defines an Indigo-style right-handed stereo pyramid which
    # correctly encodes RXN parity wrt RXN atom indeces
    for stereo_index in stereocenter_data:

        # First, sort atoms by increasing RXN index (as per Accelrys' "ctfile.pdf", page 89).
        # This puts atoms in a correct clockwise parity.
        pyramid = [x[0] for x in sorted(stereocenter_data[stereo_index]["pyramid"], key=lambda x: x[1])]
        # Then, if parity is really counterclockwise...
        if stereocenter_data[stereo_index]["parity"] == 2:
            # ...swap the second and the third atoms.
            pyramid = [pyramid[0], pyramid[2], pyramid[1], pyramid[3]]

        # Finally, set this stereo config to the Indigo stereocenter.
        # Note: the function "addStereocenter" is not properly documented, so the usage here is based
        # on my best guess. See <https://groups.google.com/forum/#!topic/indigo-dev/oWTt3OSF8FM>.
        #print "STEREO DATA", str(pyramid)
        imol.getAtom(stereo_index).addStereocenter(Indigo.ABS, pyramid[0], pyramid[1], pyramid[2], pyramid[3])

    # Force layout, because if you don't, the stereo bonds will be rendered as flat.
    imol.layout()

    # So if you don't want auto layout, restore the original coordinates.
    if not layout:
        for i, (x, y, z) in xyz.iteritems():
            imol.getAtom(i).setXYZ(x, y, z)

    # Fold hydrogens. This may need to be made settable.
    imol.foldHydrogens()  # This destroys stereo data

    return imol


def add_actors_to_ireaction(indigo, actors, addfunc, layout=False):
    """ Adds groups of molecules (reactants, agents, products) to an Indigo reaction. """

    # For every chem.Molecule object in the given group, construct an equivalent Indigo molecule.
    for mol in actors:
        imol = build_indigo_molecule(mol, indigo, layout)

        # Add indigo molecule to indigo reaction.
        # This, unfortunately, copies the molecule to reaction object and returns 1 on success.
        # No standard way to get a reference to that copy to set the mapping numbers.
        # (Because the aam setter function belongs to the reaction class, not molecule).
        addfunc(imol)


def renderReactionToBuffer(reaction, render_format="png", layout=False):
    (indigo, renderer) = get_indigo()

    if render_format == "svg":
        indigo.setOption("render-image-size", 800, -1)
        indigo.setOption("render-output-format", "svg")
    else:
        indigo.setOption("render-image-size", 940, -1)
        indigo.setOption("render-output-format", "png")

    ireaction = build_indigo_reaction(reaction, indigo, layout, layout, layout)

    return renderer.renderToBuffer(ireaction)


def renderMoleculeToBuffer(molecule, render_format="png", layout=False, highlight=False):
    (indigo, renderer) = get_indigo()
    #indigo.setOption("render-image-size", 220, 119)

    if render_format == "svg":
        indigo.setOption("render-output-format", "svg")
    else:
        indigo.setOption("render-output-format", "png")

    if highlight:
        indigo.setOption("render-background-color", 1.0, 0.9, 0.8)

    imol = build_indigo_molecule(molecule, indigo, layout)

    return renderer.renderToBuffer(imol)


def renderRGroupToBuffer(reaction, rname, nmol, render_format="png", layout=False):
    (indigo, renderer) = get_indigo()

    if rname not in reaction.rgroups.keys() or nmol >= len(reaction.rgroups[rname]):
        return None

    if render_format == "svg":
        indigo.setOption("render-output-format", "svg")
    else:
        indigo.setOption("render-output-format", "png")

    mol = reaction.rgroups[rname][nmol]

    imol = build_indigo_molecule(mol, indigo, layout)

    return renderer.renderToBuffer(imol)


class SVGRenderer:
    """
      This class exists for the sole purpose of handling Indigo's shameful ways
      of generating svg files. The class methods are exactly as before, except
      now the renderer object will store the glyph names it's previously seen
      and will rename subsequent svg glyphs to avoid conflicts. Thus, as long as
      the same renderer object is used for generating svg images that appear
      on the same html page, there should be no conflicts.
    """

    def __init__(self):
        """
            self.names dictionary maps glyph names to the number of times they have been used,
            e.g., { "glyph0-1" : 7 }
        """
        self.names = {}

    def renderReactionToBuffer(self, reaction, layout=False):
        (indigo, renderer) = get_indigo()
        indigo.setOption("render-image-size", 800, -1)
        indigo.setOption("render-output-format", "svg")

        ireaction = build_indigo_reaction(reaction, indigo, layout, layout, layout)
        raw_xml = renderer.renderToBuffer(ireaction)

        return self.fix_xml(raw_xml)


    def renderMoleculeToBuffer(self, molecule, layout=False):
        (indigo, renderer) = get_indigo()
        indigo.setOption("render-output-format", "svg")

        imol = build_indigo_molecule(molecule, indigo, layout)
        raw_xml = renderer.renderToBuffer(imol).tostring()

        return self.fix_xml(raw_xml)


    def renderRGroupToBuffer(self, reaction, rname, nmol, layout=False):
        (indigo, renderer) = get_indigo()

        if rname not in reaction.rgroups.keys() or nmol >= len(reaction.rgroups[rname]):
            return None

        indigo.setOption("render-output-format", "svg")

        mol = reaction.rgroups[rname][nmol]

        imol = build_indigo_molecule(mol, indigo, layout)
        raw_xml = renderer.renderToBuffer(imol)

        return self.fix_xml(raw_xml)


    def fix_xml(self, raw_xml):
        import xml.etree.ElementTree as ET

        # Set up the namespaces
        ns = {'default': 'http://www.w3.org/2000/svg',
              'xlink': 'http://www.w3.org/1999/xlink'}

        for key, val in ns.iteritems():
            mykey = key
            if key == "default" :
                mykey = ""
            ET.register_namespace(mykey, val)

        # Parse the raw xml
        root = ET.fromstring(raw_xml)

        # Renaming scheme; maps old glyph name to a new one
        rename_to = {}

        # Iterate over name definitions
        for symbol in root.findall("default:defs/default:g/default:symbol", ns):
            if symbol.attrib["id"] in self.names:
                self.names[symbol.attrib["id"]] +=1
            else:
                self.names[symbol.attrib["id"]] = 0

            rename_to[symbol.attrib["id"]] = "%s-%s" % (symbol.attrib["id"], str(self.names[symbol.attrib["id"]]))
            #print "Will rename", symbol.attrib["id"], "to", rename_to[symbol.attrib["id"]]

            symbol.attrib["id"] = rename_to[symbol.attrib["id"]]

        # print "Renaming scheme:"
        # print str(rename_to)

        # Iterate over name instances
        for use in root.findall("default:g/default:g/default:use", ns):
            key = "{%s}href" % ns["xlink"]
            clean_id = use.attrib[key][1:]  # Get rid of the leading '#'
            if clean_id in rename_to:
                use.attrib[key] = "#" + rename_to[clean_id]

        return ET.tostring(root, encoding="UTF-8", method="xml")


# DEBUGGINGS
# import rxn
# reac = rxn.parse_rxn("../ltefServer/reactions/rxn/alkyne_hydrogenation_with_lindlars_catalyst.rxn")
# molecule = reac.reactants[0]
# r = SVGRenderer()
# print r.renderMoleculeToBuffer(molecule)
#
# print "\n"*5
# print "* " * 40
# print r.renderReactionToBuffer(reac)
#
# print r.renderRGroupToBuffer(reac, "R1", 0)
