def get_pddl_atom_name_from_atom(atom):
    return atom.symbol.lower() + str(atom.rxnAAM)


def pddl_op(op, myList):
    if len(myList) > 1:
        return "(%s %s)" % (op, " ".join(myList))
    elif len(myList) == 1:
        return myList[0]
    else:
        return "You are doing it wrong."


def get_atom_name_from_symbol(symbol):
    name = "atom"

    atomNames = {
        "C" : "carbon",
        "H" : "hydrogen",
        "O" : "oxygen",
        "N" : "nitrogen",
        "K" : "potassium",
    }

    if symbol in atomNames.keys() :
        name = atomNames[symbol]

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

def getDomain(reaction):
    """ This must only be run on a generic reaction!
        This method is bound to be naive and inefficient...
    """

    size = reaction.numberOfAtoms + 1   # To avoid messing with adding and subtracting

    # Compute parameters and effects

    effects = []
    parameters = {}

    # Initialize bond matrices to 0
    bondMatrixBefore = [list(i) for i in [[None]*size]*size]
    for mol in reaction.reactants:
        for bond in mol.bondList:
            bondMatrixBefore[bond.fromAtom.rxnAAM][bond.toAtom.rxnAAM] = bond
            bondMatrixBefore[bond.toAtom.rxnAAM][bond.fromAtom.rxnAAM] = bond

    bondMatrixAfter = [list(i) for i in [[None]*size]*size]
    for mol in reaction.products:
        for bond in mol.bondList:
            bondMatrixAfter[bond.fromAtom.rxnAAM][bond.toAtom.rxnAAM] = bond
            bondMatrixAfter[bond.toAtom.rxnAAM][bond.fromAtom.rxnAAM] = bond


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

                atomName1 = get_pddl_atom_name_from_atom(bond.fromAtom)
                atomName2 = get_pddl_atom_name_from_atom(bond.toAtom)

                parameters[atomName1] = get_atom_name_from_symbol(bond.fromAtom.symbol)
                parameters[atomName2] = get_atom_name_from_symbol(bond.toAtom.symbol)

                if bondMatrixBefore[x][y] is not None:  # There is a bond that disappears
                    effects.append("(not (" + get_bond_name_from_order(bondMatrixBefore[x][y].order) + " ?" + atomName1 + " ?" + atomName2 + "))")

                if bondMatrixAfter[x][y] is not None:  # There is a bond that is created
                    effects.append("(" + get_bond_name_from_order(bondMatrixAfter[x][y].order) + " ?" + atomName1 + " ?" + atomName2 + ")")




    # Compute preconditions
    # Precondition simply describes the reactants

    # All reaction preconditions
    preconditions = []

    for mol in reaction.reactants:
        # Preconditions due to this particular molecule
        prec = []
        nonparameters = {}

        for bond in mol.bondList:

            atom1 = bond.fromAtom
            atom2 = bond.toAtom
            atomName1 = get_pddl_atom_name_from_atom(atom1)
            atomName2 = get_pddl_atom_name_from_atom(atom2)

            for (atomName, atom) in zip([atomName1, atomName2], [atom1, atom2]):
                if atomName not in parameters.keys() and atomName not in nonparameters.keys():
                    nonparameters[atomName] = atom

            prec.append("(" + get_bond_name_from_order(bond.order) + " ?" + atomName1 + " ?" + atomName2 + ")")

        prec_string = ""


        if len(nonparameters.keys()) > 0:
            for nonparam, atom in nonparameters.iteritems():
                if atom.symbol in reaction.rgroups.keys():
                    pass
                    #print "This non-parameter is an r-group " + atom.symbol + " with " + str(len(reaction.rgroups[atom.symbol])) + " possible values"
                #nonparam_prec = ""
                #prec.append(nonparam_prec)

            prec_string = "(exists (?" + " - atom ?".join(nonparameters.keys()) + " - atom) " + pddl_op("and", prec) + ")"
        else:
            prec_string = pddl_op("and", prec)

        preconditions.append(prec_string)




    pddl_domain = "(:action " + reaction.name
    pddl_domain += "\n:parameters (?" + " ?".join(["%s - %s" % (atomName, parameters[atomName]) for atomName in parameters.keys()]) + ")"
    pddl_domain += "\n:precondition " + pddl_op("and", preconditions)
    pddl_domain += "\n:effect " + pddl_op("and", effects) + ")"

    return pddl_domain

