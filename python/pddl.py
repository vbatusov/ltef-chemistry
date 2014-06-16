
def get_atom_name_from_symbol(symbol):
    name = "unknownAtom"

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

    effects = ""
    posEffects = {}
    negEffects = {}
    affected = {}

    size = reaction.numberOfAtoms + 1   # To avoid messing with adding and subtracting

    # Initialize bond matrices to 0
    bondMatrixBefore = [list(i) for i in [[0]*size]*size]
    for mol in reaction.reactants:
        for bond in mol.bondList:
            bondMatrixBefore[bond.fromAtom.rxnAAM][bond.toAtom.rxnAAM] = bond
            bondMatrixBefore[bond.toAtom.rxnAAM][bond.fromAtom.rxnAAM] = bond

    bondMatrixAfter = [list(i) for i in [[0]*size]*size]
    for mol in reaction.products:
        for bond in mol.bondList:
            bondMatrixAfter[bond.fromAtom.rxnAAM][bond.toAtom.rxnAAM] = bond
            bondMatrixAfter[bond.toAtom.rxnAAM][bond.fromAtom.rxnAAM] = bond


    print bondMatrixBefore
    print bondMatrixAfter

    # Is there a Pythonic way of doing this?
    for x in range(1, size):
        for y in range(x + 1, size):
            if bondMatrixBefore[x][y] != bondMatrixAfter[x][y]:
                # Means both involved atoms are "affected" and must be action parameters; bond change contributes to effects
                print "Bond between #" + str(x) + " and #" + str(y) + " has changed from " + str(bondMatrixBefore[x][y]) + " to " + str(bondMatrixAfter[x][y])

                #atomName1 = 

                #affected[x]



    

    return ""

