import chem
import itertools
import re

""" The PDDL output is inspired by and modeled after Andrea's "domain_macro_V1.pddl" file.

    Note to self: there is trouble with r-groups. Why do the various "get_..._description" methods
    differ in the type of arguments? This will cause a mess with R-groups.
"""

def get_pddl_atom_name_from_atom(atom):
    name = atom.symbol

    atomSymbols = chem.pseudoatomToList(atom.symbol)
    if len(atomSymbols) > 1:
        name = ""
        for s in atomSymbols:
            if s in chem.LIST_TRANSLATION.keys():
                name += chem.LIST_TRANSLATION[s]
            else:
                name += s
    result = chem.sanitize_name(name) + "_" + str(atom.aam)

    return result

def get_atom_description(reaction, atom):
    """ Let a PDDL atom description consist of:
        - atom name: c1, h3, alkyl5, r12, hmethyl4
        - atom pddl type: carbon, hydrogen, atom, atom, atom
        - atom description: "", "", "(alkyl ?alkyl5)", "(or (alkyl ?r12) (hydrogen ?r12))", "(or (hydrogen ?hmethyl4) (methyl ?hmethyl4))"
        Note that, in case of hydrogen, there is a collision of type and predicate.
        It may be necessary to create derived predicates "p_<name>", like

        (:predicates ...
            (p_hydrogen ?h - hydrogen)
        ...)
        (:derived (p_hydrogen ?h - hydrogen) (= ?h ?h)))

        Ignore this for now; assume type can be used as a predicate.

        A further problem is that an R-group may be a multi-atom molecule. Ignore this as well; assume it's a simple atom.
        Update (2014-12-19): Need to handle R-groups like [H,C,N,O], i.e. disjunctions of atoms. But not multi-atom molecules.
    """
    #print "Invoking get_atom_description on symbol " + atom.symbol

    atomName = get_pddl_atom_name_from_atom(atom)
    atomType = get_atom_pddl_type_from_symbol(atom.symbol)
    atomDesc = ""

    #print "  atomName=" + atomName

    if atomType == "object":  # Not a simple atom, begs a non-empty description
        atomSymbols = chem.pseudoatomToList(atom.symbol)   
        #print "  atomSymbols=" + str(atomSymbols)
        if len(atomSymbols) > 1:
            # This is a "list" atom, yields a disjunction of possible atoms
            atomDescList = []
            for eachSymbol in atomSymbols:
                actualSymbol = eachSymbol
                if eachSymbol in chem.LIST_TRANSLATION.keys():
                    actualSymbol = chem.LIST_TRANSLATION[eachSymbol]
                actualType = get_atom_pddl_type_from_symbol(actualSymbol)
                if actualType != "object":
                    atomDescList.append("(%s ?%s)" % (get_predicate_from_type(actualType), atomName))
                else:
                    atomDescList.append(get_complex_single_atom_desc(reaction, actualSymbol, atomName))
            atomDesc = pddl_op("or", atomDescList)
        else:
            atomDesc = get_complex_single_atom_desc(reaction, atom.symbol, atomName)

    return (atomName, atomType, atomDesc)


def get_complex_single_atom_desc(reaction, atomSymbol, atomName):
    #print "Invoking get_complex... on symbol " + atomSymbol
    atomDesc = ""

    # It's a single atom, possibly a pseudo-atom, possibly an r-group
    if chem.sanitize_name(atomSymbol) in chem.PSEUDO.keys():
        # A pseudoatom description is simply a derived predicate;
        # the PSEUDO list must be complete for this to work.
        atomDesc = "(%s ?%s)" % (chem.sanitize_name(atomSymbol), atomName)
    elif atomSymbol in reaction.rgroups.keys():
        # An r-group description is a disjunction of the descriptions of
        # the molecules forming the corresponding r-group in the reaction.
        atomDescList = []
        for mol in reaction.rgroups[atomSymbol]:
            #print " looking at r-group " + str(mol) + " with anchor " + str(mol.anchor)
            if chem.sanitize_name(mol.anchor.symbol) in chem.PSEUDO.keys():
                atomDescList.append("(%s ?%s)" % (chem.sanitize_name(mol.anchor.symbol), atomName))
            else:
                temp = get_atom_pddl_type_from_symbol(mol.anchor.symbol)
                atomSymbols = chem.pseudoatomToList(mol.anchor.symbol)
                if len(atomSymbols) > 1:
                    # See if it's a list; if it is, expand it into a disjunction
                    nestedAtomDescs = [get_atom_description(reaction, chem.Atom(sym, 0, 0, 0, 0, 0)) for sym in atomSymbols]
                    atomDescList.append(pddl_op("or", ["(%s ?%s)" % (get_predicate_from_type(d[1]), atomName) for d in nestedAtomDescs]))
                else:
                    atomDescList.append("(%s ?%s)" % (get_predicate_from_type(temp), atomName))

        atomDesc = pddl_op("or", atomDescList)
    else:
        atomDesc = "(UNKNOWN)"

    #print "The complex atom desciption for " + atomSymbol + " with name " + atomName + " is " + atomDesc
    return atomDesc


def pddl_op(op, myList):
    if len(myList) > 1:
        return "(%s %s)" % (op, " ".join(myList))
    elif len(myList) == 1:
        return myList[0]
    else:
        return ""

def pddl_not_equal(name1, name2):
    return "(not (= ?%s ?%s))" % (name1, name2)


def get_atom_pddl_type_from_symbol(symbol):
    name = "object"

    if symbol in chem.ATOM_NAMES.keys() :
        name = chem.ATOM_NAMES[symbol]

    return name


def get_bond_name_from_order(order):
    name = "unknownBond"

    bondNames = {
        1 : "bond",
        2 : "doubleBond",
        3 : "tripleBond",
        4 : "aromaticBond"
    }

    if order in bondNames.keys():
        name = bondNames[order]

    return name

def get_predicate_from_type(type):
    return "p" + type[0].upper() + type[1:]


def store_atom_in_type_dict(dic, typ, atomName):
    if typ not in dic.keys():
        dic[typ] = []

    if atomName not in dic[typ]:
        dic[typ].append(atomName)


def get_inequalities(dictionary):
    ineq = []

    for names in dictionary.values():
        for (name1, name2) in itertools.combinations(names, 2):
            ineq.append(pddl_not_equal(name1, name2))

    return ineq


def getDomain(reaction):
    """ This must only be run on a generic reaction!
        This method is bound to be naive and inefficient...
    """

    size = reaction.numberOfAtomsOverall + 1   # To avoid messing with adding and subtracting

    # Compute parameters and effects

    effects = []
    parameters = {}
    parametersByType = {}
    parameterAtoms = {} # Maps AAM to atom object

    # Initialize bond matrices to 0
    bondMatrixBefore = [list(i) for i in [[None]*size]*size]
    for mol in reaction.reactants:
        for bond in mol.bondList:
            bondMatrixBefore[bond.fromAtom.aam][bond.toAtom.aam] = bond
            bondMatrixBefore[bond.toAtom.aam][bond.fromAtom.aam] = bond

    bondMatrixAfter = [list(i) for i in [[None]*size]*size]
    for mol in reaction.products:
        for bond in mol.bondList:
            bondMatrixAfter[bond.fromAtom.aam][bond.toAtom.aam] = bond
            bondMatrixAfter[bond.toAtom.aam][bond.fromAtom.aam] = bond


    #print bondMatrixBefore
    #print bondMatrixAfter

    # Is there a Pythonic way of doing this?
    for x in range(1, size):
        for y in range(x + 1, size):
            if not bondMatrixBefore[x][y] == bondMatrixAfter[x][y]:
                # Means both involved atoms are "affected" and must be action parameters; bond change contributes to effects
                #print "Bond between #" + str(x) + " and #" + str(y) + " has changed from " + str(bondMatrixBefore[x][y]) + " to " + str(bondMatrixAfter[x][y])
                
                bond = None
                if bondMatrixBefore[x][y] is not None:
                    bond = bondMatrixBefore[x][y]
                else:
                    bond = bondMatrixAfter[x][y]

                parameterAtoms[bond.fromAtom.aam] = bond.fromAtom
                parameterAtoms[bond.toAtom.aam] = bond.toAtom

                atomName1 = get_pddl_atom_name_from_atom(bond.fromAtom)
                atomName2 = get_pddl_atom_name_from_atom(bond.toAtom)

                parameters[atomName1] = get_atom_pddl_type_from_symbol(bond.fromAtom.symbol)
                parameters[atomName2] = get_atom_pddl_type_from_symbol(bond.toAtom.symbol)

                store_atom_in_type_dict(parametersByType, parameters[atomName1], atomName1)
                store_atom_in_type_dict(parametersByType, parameters[atomName2], atomName2)

                if bondMatrixBefore[x][y] is not None:  # There is a bond that disappears
                    effects.append("(not (" + get_bond_name_from_order(bondMatrixBefore[x][y].order) + " ?" + atomName1 + " ?" + atomName2 + "))")
                    effects.append("(not (" + get_bond_name_from_order(bondMatrixBefore[x][y].order) + " ?" + atomName2 + " ?" + atomName1 + "))")

                if bondMatrixAfter[x][y] is not None:  # There is a bond that is created
                    effects.append("(" + get_bond_name_from_order(bondMatrixAfter[x][y].order) + " ?" + atomName1 + " ?" + atomName2 + ")")
                    effects.append("(" + get_bond_name_from_order(bondMatrixAfter[x][y].order) + " ?" + atomName2 + " ?" + atomName1 + ")")


    # Derive a list of parameter inequalities
    paramIneq = get_inequalities(parametersByType)

    # Compute preconditions
    # Precondition describes the reactants and catalysts

    # Preconditions associated solely with properties of atoms appearing in the parameters
    #print "=========== NEW STUFF ============="
    paramPrecPredicates = []
    for paramAtom in parameterAtoms.values():
        #print str(paramAtom) + " is a " + str(get_atom_description(reaction, paramAtom))
        predicate = get_atom_description(reaction, paramAtom)[2]
        if len(predicate) > 0:
            paramPrecPredicates.append(predicate)
    paramPrec = pddl_op("and", paramPrecPredicates)
    #print "paramPrec is " + paramPrec

    #print "==================================="

    # All reaction preconditions
    preconditions = []

    for mol in reaction.reactants + reaction.agents:
        print "Processing molecule " + str(mol)
        # Preconditions due to this particular molecule
        precMol = []
        nonparameters = {}
        affectedByType = {}

        # Go over bonds, access atoms, get their properties, describe in pddl
        if len(mol.bondList) > 0:
            for bond in mol.bondList:

                atom1 = bond.fromAtom
                atom2 = bond.toAtom

                (atomName1, atomType1, atomDesc1) = get_atom_description(reaction, atom1)
                (atomName2, atomType2, atomDesc2) = get_atom_description(reaction, atom2)

                for (atomName, atomType, atomDesc) in zip([atomName1, atomName2], [atomType1, atomType2], [atomDesc1, atomDesc2]):
                    
                    if atomName not in parameters.keys() and atomName not in nonparameters.keys():
                        #print "Adding non-parameter " + atomName + " with type " + atomType + " and desc " + atomDesc
                        nonparameters[atomName] = (atomType, atomDesc)
                        # add the new nonparameter precondition if it is not a simple atom; simpe atoms are instead typed by "exists"
                        if atomDesc != "":
                            precMol.append(atomDesc)

                    store_atom_in_type_dict(affectedByType, atomType, atomName)


                # Add the molecule structure to precondition
                precMol.append("(" + get_bond_name_from_order(bond.order) + " ?" + atomName1 + " ?" + atomName2 + ")")

        elif len(mol.atomList) > 0: # Assume == 1, because it's meaningless otherwise
            if len(mol.atomList) != 1:
                raise Exception("A bondless molecule must have a single atom, no more, no less.")
                # Thought: can there be a two-atom 'molecule' with an electrostatic bond?

            atom = mol.atomList[0]
            (atomName, atomType, atomDesc) = get_atom_description(reaction, atom)
            if atomName not in parameters.keys() and atomName not in nonparameters.keys():
                #print "Adding non-parameter " + atomName + " with type " + atomType + " and desc " + atomDesc
                nonparameters[atomName] = (atomType, atomDesc)
                # add the new nonparameter precondition if it is not a simple atom; simpe atoms are instead typed by "exists"
                if atomDesc != "":
                    precMol.append(atomDesc)

            store_atom_in_type_dict(affectedByType, atomType, atomName)

        else:
            raise Exception("Stumbled upon an empty molecule! No bonds, no atoms, no nothing.")


        # Derive inequalities for the molecule, remove ones already mentioned on reaction level
        affectedIneq = list(set(get_inequalities(affectedByType)) - set(paramIneq))

        precMol_str = pddl_op("and", affectedIneq + precMol)

        if len(nonparameters.keys()) > 0:
            nonpTypes_str = " ".join(["?%s - %s" % (key, nonparameters[key][0]) for key in nonparameters.keys()])
            precMol_str = "(exists (%s) %s)" % (nonpTypes_str, precMol_str)

        preconditions.append(precMol_str)

    

    pddl_domain = "(:action " + reaction.name
    pddl_domain += "\n:parameters (?" + " ?".join(["%s - %s" % (atomName, parameters[atomName]) for atomName in parameters.keys()]) + ")"
    pddl_domain += "\n:precondition " + pddl_op("and", paramIneq + paramPrecPredicates + preconditions)
    pddl_domain += "\n:effect " + pddl_op("and", effects) + ")"

    return pddl_domain

