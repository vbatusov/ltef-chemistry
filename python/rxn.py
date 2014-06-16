import textfsm
import re
import chem
import sys
#sys.path.append('/home/vitaliy/chemistry/indigo-python-1.1.12/')
#from indigo import *
#from indigo_renderer import *
import base64
import os

(ACTOR_TYPE,
ACTOR_ARG,
RLOGIC,
ACTOR_CHIRAL,
ATOM_INDEX,
ATOM_TYPE,
ATOM_X,
ATOM_Y,
ATOM_Z,
ATOM_AAM,
ATOM_ATTR,
BOND_INDEX,
BOND_TYPE,
BOND_FROM,
BOND_TO,
BOND_ATTR) = range(16)


def parse_attribs(attribs):
    """ Parse the silly RXNv3000 atom/bond parameter string 
    and store each key-value pair as a dictionary. """

    attribDict = {}

    # Matches things like "RGROUPS=(1 1) MASS=16",
    # only the 2nd and 3rd groups in each match are important
    match = re.findall('((\S+)=((\(.*?\))|([^(]\S*)))+', attribs)

    for (_,name,val,_,_) in match:
        # If value is a RXN list, turn it into a proper list
        matchVal = re.match('^\((.*)\)$',val)
        if matchVal:
            # Split the relevant group on space and discard the first (count) item
            attribDict[name] = matchVal.group(1).split()[1:]
        else:
            attribDict[name] = val

    return attribDict

def parse_record(record, rgroup=False):
    """ A record is a list of strings and lists of strings.
    Each record defines a single (possibly generic) molecule. However,
    a definition of a single R-group may consist of multiple molecules.
    Thus, an R-group should be a list of molecules, and so parse_record
    should return not simply a molecule, but also a note about
    which R-group the molecule belongs to."""
    
    # This will be returned
    molecule = chem.Molecule()

    # A map from rxn index to the corresponding atom object,
    # necessary for creating bonds later
    indexToAtom = {}

    # Extract the defining properties of each atom from the record using pre-defined position indeces
    for (index, symbol, x, y, z, aam, attr) in zip(record[ATOM_INDEX], record[ATOM_TYPE], record[ATOM_X], record[ATOM_Y], record[ATOM_Z], record[ATOM_AAM], record[ATOM_ATTR]):
        
        # Convert the attribute string to a dictionary
        attrDict = parse_attribs(attr)

        # Correct the symbol if it is an R-group
        if symbol == "R#":
            symbol = "R" + attrDict["RGROUPS"][0]
        
        # Create an atom object
        atom = chem.Atom(symbol, float(x), float(y), float(z), int(index), int(aam), attrDict)
        indexToAtom[index] = atom

        # Add atom to molecule
        molecule.addAtom(atom)

        if rgroup and attrDict["ATTCHPT"] == "1":
            molecule.anchor = atom


    # Extract the defining properties of each bond
    for (index, order, fromAtom, toAtom, attr) in zip(record[BOND_INDEX], record[BOND_TYPE], record[BOND_FROM], record[BOND_TO], record[BOND_ATTR]):

        attrDict = parse_attribs(attr)

        # Create a bond object: to- and from-atom arguments are actual objects;
        # their RXN indeces are preserved in the objects themselves
        bond = chem.Bond(int(index), int(order), indexToAtom[fromAtom], indexToAtom[toAtom], attrDict)

        # Add bond to molecule
        molecule.addBond(bond)

    #print str(molecule) + "\n"
    

    # # DEBUG render the molecule; this tests both structure and indigo interaction
    # indigo_molecule = molecule.getIndigoObject(indigo)
    # smiles = indigo_molecule.canonicalSmiles()
    # #print "Created new " + str(molecule) + " with SMILES " + smiles
    # safename = base64.urlsafe_b64encode(smiles)
    # indigo_molecule.layout()
    # renderer.renderToFile(indigo_molecule, "img/raw-" + safename + ".png");
    # print " -> Written the molecule image to " + safename + ".png"

    return molecule

def parse_rxn(rxn, fsm="rxn.fsm"):
    """ Parses the silly RXNv3000 and creates a generic reaction as a result.
    Hack: (TODO) when reading raw data, merge lines on dash. This will elegantly (in some sense)
    handle the silly RXNv3000 80-char ugliness without making a mess out of the FSM.
    """

    # Load the regex
    re_table = textfsm.TextFSM(open(fsm))

    # Load the raw RXN
    lineList_raw = open(rxn).readlines()
    lineList = []

    # Combine multiline records into long lines
    # In RXN v3000, if a line doesn't fit into 80 chars, it is broken using a hyphen
    prefix = ''
    for line in lineList_raw:
        # If the line does not terminate...
        if line[-2:] == '-\n':
            # ...and if the previous line did not terminate...
            if len(prefix) > 0:
                # ...append line (less "M  V30 " and "-\n") to prefix
                prefix += line[7:-2]
            # ...but if the previous line terminated...
            else:
                # ...append line less "-\n" to prefix
                prefix += line[:-2]
        # If the line terminates...
        else:
            # ...and completes some preceding lines...
            if len(prefix) > 0:
                # ...store the complete line; don't forget to cut off "M  V30 " and clear prefix
                lineList.append(prefix + line[7:])
                prefix = ''
            # If there is no prefix, just store the line
            else:
                lineList.append(line)

    # Concatenate lines into a single string
    text = ''.join(lineList)

    # Parse the RXN using the state machine
    # Data is a list of TextFSM records
    data = re_table.ParseText(text)

    # This will be returned
    reaction = chem.Reaction()

    # Reminder: each record stores a complete description of a single molecule
    for record in data:
        #print record
        if record[ACTOR_TYPE]=="REACTANT":
            #print "Found reactant"
            reaction.addReactant(parse_record(record))

        elif record[ACTOR_TYPE]=="PRODUCT":
            #print "Found product"
            reaction.addProduct(parse_record(record))

        elif record[ACTOR_TYPE]=="AGENT":
            #print "Found agent"
            reaction.addAgent(parse_record(record))

        elif record[ACTOR_TYPE]=="RGROUP":
            #print "Found an R-group"
            reaction.addRGroup(record[ACTOR_ARG], parse_record(record, True))

        else:
            raise Exception("Unknown record type!")

    return reaction


# print "\n\n************   S T A R T   A G A I N   **************\n"

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

