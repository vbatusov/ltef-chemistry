import copy
import random
import re

class Atom:
    'This class is geared to store atom information supplied by v3000 molfiles'

    def __init__(self, symbol, x, y, z, rxnIndex, rxnAAM, attribs={}, aam=0):
        self.symbol = symbol
        self.aam = aam # This a working, sanitized AAM, doesn't have to be the same as rxnAAM
        self.x = x
        self.y = y
        self.z = z
        self.rxnIndex = rxnIndex
        self.rxnAAM = rxnAAM
        self.attribs = attribs
        self.mass = 0
        self.charge = 0

    def __str__(self):
        return "<Atom " + self.symbol + " at (" + ", ".join([str(self.x), str(self.y), str(self.z)]) + ") with AAM=" + str(self.aam) + " (old rxn " + str(self.rxnAAM) + ") and attribs " + str(self.attribs) + " />"

    def __eq__(self, other):
        return type(self) == type(other) and self.symbol == other.symbol and self.aam == other.aam and self.charge == other.charge

class Bond:
    'v3000 bond information container'

    'fromAtom and toAtom must be Atom objects!'
    def __init__(self, rxnIndex, order, fromAtom, toAtom, attribs={}):
        self.rxnIndex = rxnIndex
        self.order = order
        self.fromAtom = fromAtom
        self.toAtom = toAtom
        self.attribs = attribs

    def __str__(self):
        return "<Bond with order " + str(self.order) + " between AAM " + str(self.fromAtom.aam) + " and " + str(self.toAtom.aam) + " />"

    def __eq__(self, other):
        #print "(comparing bonds)"
        #print "  self: " + str(self)
        #print "  other: " + str(other)

        return type(self) == type(other) and self.order == other.order and ((self.fromAtom == other.fromAtom and self.toAtom == other.toAtom) or (self.fromAtom == other.toAtom and self.toAtom == other.fromAtom))

    def getOtherAtom(self, atom):
        if self.fromAtom == atom:
            return self.toAtom
        else:
            return self.fromAtom

class Molecule:
    """ A molecule can be either a complete molecule or a fragment.
    The difference is in the self.anchor: it is the attachment point
    which for a fragment is a pointer to one of its atoms and for a
    complete molecule is None.

    A molecule may contain pseudoatoms ("Alkyl") and R-group atoms ("R1").
    """

    def __init__(self):
        self.atomList = []
        self.bondList = []
        self.anchor = None

    def addAtom(self, *atom):
        for a in atom:
            #print "Adding atom " + str(a)
            self.atomList.append(a)

    def addBond(self, bond):
        self.bondList.append(bond)

    def __str__(self):
        desc = "<Molecule>"
        for atom in self.atomList:
            desc += "\n  " + str(atom)
        for bond in self.bondList:
            desc += "\n  " + str(bond)
        desc += "\n</Molecule>"
        return desc

    def inferAtomsFromBonds(self):
        """
        discards self.atomList, replaces it with an array of atoms gathered from bonds
        """
        self.atomList = []
        #print "Recomputing atoms"
        for b in self.bondList:
            if b.toAtom not in self.atomList:
                self.atomList.append(b.toAtom)
                #print "Adding atom with aam " + str(b.toAtom.aam)
            if b.fromAtom not in self.atomList:
                self.atomList.append(b.fromAtom)
                #print "Adding atom with aam " + str(b.fromAtom.aam)
    def isDiatomicHalogen(self):
        if (len(self.bondList) == 1 and len(self.atomList) == 2 and
                self.atomList[0].symbol == "X" and self.atomList[1].symbol == "X"):
            #print "This molecule is a diatomic halogen: " + str(self)
            return True
        return False

    @property
    def numberOfAtoms(self):
        return len(self.atomList)

    def replaceAtomWithMolecule(self, oldatom, newmolecule):
        """ Used by Molecule.getInstance, this method alters 'self' by replacing a given atom
        object with another one in atomList, and then correcting the bonds to point to the
        new atom. Finally, the remaining atoms and bonds in given molecule are added to 'self'.
        """

        if newmolecule.anchor is None:
            raise Exception("New molecule does not have an anchor!")

        newmolecule.anchor.aam = oldatom.aam

        # Correct the bonds to anchor of new molecule
        for bond in self.bondList:
            if bond.toAtom is oldatom:
                bond.toAtom = newmolecule.anchor
            if bond.fromAtom is oldatom:
                bond.fromAtom = newmolecule.anchor

        # Add remaining atoms and bonds to current molecule
        self.atomList = filter(lambda a: a is not oldatom, self.atomList)
        self.atomList.extend(newmolecule.atomList)  # Is extend shallow or deep? Assume shallow.
        self.bondList.extend(newmolecule.bondList)


        # FINISHED, UNTESTED


    def getInstance(self, rgroups={}):
        """ This returns a new molecule which is the same as self except that every
        R-atom is replaced with a corresponding molecule from the provided dictionary.
        """
        # This will be returned
        newmol = copy.deepcopy(self)

        #print "Molecule instantiation in progress..."
        #print "New copy of original:\n" + str(newmol)

        # In the copy, replace each occurence of an R-atom with an actual R-instance
        for atom in newmol.atomList:
            #print "Looking at atom " + atom.symbol
            if atom.symbol in rgroups.keys():
                #print "An R-group is found! Replacing it with a sub-molecule..."
                newmol.replaceAtomWithMolecule(atom, rgroups[atom.symbol])

        #print "molecule.getInstance: ORIGINAL\n" + str(self)
        #print "molecule.getInstance: RESULT\n" + str(newmol)

        return newmol

        # FINISHED, UNTESTED




class Reaction:
    """stores a set of reactants, agents, products, and rgroups

    rgroups is a dictionary "R1" : [R-molecule, R-molecule, ...]
    """

    def __init__(self, name="unknown_reaction", full_name="Unknown Reaction", desc="No description"):
        self.desc = desc    # reaction description from text file
        self.name = name    # basename (unique identifier), also used as reaction name in PDDL
        self.full_name = full_name  # Official human-readable name from YAML file
        self.params = {}    # for instantiation parameters; generic reaction params are {}
        self.reactants = []
        self.agents = []
        self.products = []
        self.rgroups = {}


    def __str__(self):
        desc = "<Reaction>"
        desc += "\n  <Reactants>"
        for r in self.reactants:
            desc += "\n    " + ('\n    ').join(str(r).split('\n'))
        desc += "\n  </Reactants>\n  <Agents>"
        for a in self.agents:
            desc += "\n    " + ('\n    ').join(str(a).split('\n'))
        desc += "\n  </Agents>\n  <Products>"
        for p in self.products:
            desc += "\n    " + ('\n    ').join(str(p).split('\n'))
        desc += "\n  </Products>\n  <R-groups>"
        for g in self.rgroups.keys():
            desc += "\n    <R-group No. " + g + ">"
            for g2 in self.rgroups[g]:
                desc += "\n      " + ('\n      ').join(str(g2).split('\n'))
            desc += "\n    </R-group No. " + g + ">"
        desc += "\n  </R-groups>\n<Reaction>"

        return desc

    @property
    def numberOfAtomsInReactants(self):
        """ Counts all atoms (including pseudoatoms and R-atoms) in reactants.
        """
        num = 0

        for mol in self.reactants:
            num += mol.numberOfAtoms

        return num

    @property
    def numberOfAtomsOverall(self):
        """ Counts all atoms (including pseudo and R) in reaction,
        including catalysts.
        """
        num = self.numberOfAtomsInReactants

        for mol in self.agents:
            num += mol.numberOfAtoms

        return num

    def addReactant(self, molecule):
        self.reactants.append(molecule)

    def addAgent(self, molecule):
        self.agents.append(molecule)

    def addProduct(self, molecule):
        self.products.append(molecule)

    def addRGroup(self, rgroupNumber, molecule):
        rgroupName = "R" + str(rgroupNumber)
        if rgroupName not in self.rgroups:
            self.rgroups[rgroupName] = []
        self.rgroups[rgroupName].append(molecule)

    def finalize(self):
        """ Merely a sanity check
        Only execute after everything has been added to reaction.
        """

        aamReactants = []
        aamAgents = []
        aamProducts = []

        for mol in self.reactants:
            for atom in mol.atomList:
                #print "Sanity: " + str(atom)
                if atom.aam == 0:
                    raise Exception("Sanity check: reaction contains a reactant atom with AAM = 0")
                if atom.aam in aamReactants:
                    raise Exception("Sanity check: reaction contains two reactant atoms with the same AAM, #" + str(atom.aam) + ";\n current atom: " + str(atom))
                else:
                    aamReactants.append(atom.aam)

        for mol in self.agents:
            for atom in mol.atomList:
                if atom.aam == 0:
                    raise Exception("Sanity check: reaction contains a catalyst atom with AAM = 0")
                if atom.aam in aamAgents:
                    raise Exception("Sanity check: reaction contains two catalyst atoms with the same AAM, #" + str(atom.aam) + ";\n current atom: " + str(atom))
                else:
                    aamAgents.append(atom.aam)

        for mol in self.products:
            for atom in mol.atomList:
                if atom.aam == 0:
                    raise Exception("Sanity check: reaction contains a product atom with AAM = 0")
                if atom.aam in aamProducts:
                    raise Exception("Sanity check: reaction contains two product atoms with the same AAM, #" + str(atom.aam) + ";\n current atom: " + str(atom))
                else:
                    aamProducts.append(atom.aam)

        if len(set(aamReactants).intersection(set(aamProducts))) != len(aamReactants):
            print "Reaction: " + str(self.name)
            print "Reactants: " + str(aamReactants)
            print "Products: " + str(aamProducts)

            print "Reactants: " + str([str(r) for r in self.reactants])
            print "Products: " + str([str(r) for r in self.products])
            raise Exception("Sanity check: mismatch between reactant and product atom sets")

        if len(set(aamReactants).intersection(set(aamAgents))) != 0:
            raise Exception("Sanity check: reactants and catalyst share some atoms")

        if self.numberOfAtomsOverall != len(aamReactants + aamAgents):
            raise Exception("Sanity check: self.numberOfAtomsOverall != len(aamReactants + aamAgents)")

    def selectRGroups(self):
        """ For each unique R-group in reaction, select a single generic
        fragment out of the set of possible ones. Do not unroll the pseudoatoms.
        """

        # This will be returned
        fragments = {}

        # For each R-group name
        for rgroupName in self.rgroups.keys():
            # Randomly pick one fragment (one R-group may have multiple)
            fragments[rgroupName] = copy.deepcopy(random.choice(self.rgroups[rgroupName]))

        return fragments

    def getParamsTemplate():
        params = {}

        # Indicate, for each R-name, how many options there are to choose from
        for rname in self.rgroups.keys():
            if "R" not in params.keys():
                params["R"] = {}
            params["R"][rname] = range(0,len(self.rgroups[rname]))

        # Collect param templates for each pseudoatom
        for molecule in reactionInst.reactants + reactionInst.agents:
            for atom in molecule.atomList:
                #print "Looking at atom " + atom.symbol

                # If atom's symbol is an RXN string list, select one symbol arbitrarily
                atomSymbols = pseudoatomToList(atom.symbol)    # Is this a list atom?
                #print "  result of unwrapping: " + str(atomSymbols)
                if len(atomSymbols) > 1:
                    symbol_tmp = random.choice(atomSymbols)
                    #print "  selected " + symbol_tmp + " out of " + str(atomSymbols)
                    if symbol_tmp in LIST_TRANSLATION.keys():
                        atom.symbol = LIST_TRANSLATION[symbol_tmp]
                    else:
                        atom.symbol = symbol_tmp
                    #print "Set atom.symbol to " + atom.symbol

                # If atom's symbol is in pseudo, generate an actual fragment
                if sanitize_symbol(atom.symbol) in PSEUDO.keys():
                    #print "A pseudoatom is found! " + sanitize_symbol(atom.symbol)
                    fragmentsPseudo[str(atom.aam)] = getInstanceByName(atom)
                else:
                    #print "Not a pseudoatom, make a singleton molecule"
                    molecule = Molecule()
                    molecule.addAtom(atom)
                    molecule.anchor = atom
                    fragmentsPseudo[str(atom.aam)] = molecule


    def getInstance(self, params={}):
        """ Returns an instantiated (non-generic) reaction.
        Logic:
            1. For each r-group in reaction, select a generic instance and
                substitute it for the respective r-group atom on both sides
                of the reaction.
            2. For each unique pseudoatom in reaction, generate a non-generic
                instance and substitute it for the respective atom on both
                sides of reaction.
            The result should be an entirely new reaction object.

        The empty params argument yields a random instance.
        A non-empty param argument must be compatible with the reaction. Use
        the reaction.getParamsTemplate() for a template param dictionary.
        """

        # DEBUG
        #print "Building a reaction instance...\n"
        #print "Generic / source:\n" + str(self)

        # This will be returned
        reactionInst = Reaction(self.name + "_instance")

        # Select specific generic fragments to be used as R-groups
        fragmentsRG = self.selectRGroups()

        # Substitute selected R-fragments into every reactant, agent, and product
        for molecule in self.reactants:
            reactionInst.addReactant(molecule.getInstance(fragmentsRG))

        for molecule in self.agents:
            reactionInst.addAgent(molecule.getInstance(fragmentsRG))

        for molecule in self.products:
            reactionInst.addProduct(molecule.getInstance(fragmentsRG))

        # To finish with R-groups, assign AAM numbers where necessary
        # Note: it is enough to set AAM in reactants only, since they are
        # stored as references and will change across the entire reaction.
        nextAAM = reactionInst.numberOfAtomsInReactants
        for molecule in reactionInst.reactants:
            for atom in molecule.atomList:
                if atom.aam == 0:
                    atom.aam = nextAAM
                    nextAAM -= 1

        # Now, unwrap the pseudoatoms.
        # In each reactant and agent, for each pseudoatom, generate a fragment
        # and substitute with it every occurence of the pseudoatom in the products.
        # Keep a lookout for diatomic halogens!
        fragmentsPseudo = {}

        for molecule in reactionInst.reactants + reactionInst.agents:

            # Special case #1
            if molecule.isDiatomicHalogen():
                atom1 = molecule.atomList[0]
                atom2 = molecule.atomList[1]
                frag1 = getInstanceByName(atom1)  # standard way
                frag2 = buildHalogen(atom2.aam, {"symbol" : [frag1.anchor.symbol] })  # enforce same chemical element
                fragmentsPseudo[str(atom1.aam)] = frag1
                fragmentsPseudo[str(atom2.aam)] = frag2

            # General case
            else:
                for atom in molecule.atomList:

                    # Indicates that the atom is a list pseudoatom
                    listPseudo = False

                    # If atom's symbol is an RXN string list, select one symbol arbitrarily
                    atomSymbols = pseudoatomToList(atom.symbol)    # Is this a list atom?

                    if len(atomSymbols) > 1:

                        listPseudo = True
                        symbol_tmp = random.choice(atomSymbols)

                        # Rename the atom according to the choice and list translation rules
                        if symbol_tmp in LIST_TRANSLATION.keys():
                            atom.symbol = LIST_TRANSLATION[symbol_tmp]
                        else:
                            atom.symbol = symbol_tmp

                    # If atom's symbol is in pseudo, generate an actual fragment
                    if sanitize_symbol(atom.symbol) in PSEUDO.keys():
                        #print "A pseudoatom is found! " + sanitize_symbol(atom.symbol)
                        fragmentsPseudo[str(atom.aam)] = getInstanceByName(atom)

                    # If atom is not real pseudo, but was obtained from a list, still store it as a fragment
                    elif listPseudo:
                        molecule = Molecule()
                        molecule.addAtom(atom)
                        molecule.anchor = atom
                        fragmentsPseudo[str(atom.aam)] = molecule



        # Iterate through fragments and assign aam to all atoms
        nextAAM = reactionInst.numberOfAtomsOverall + 1
        for frag in fragmentsPseudo.values():
            for atom in frag.atomList:
                if atom.aam == 0:
                    atom.aam = nextAAM
                    nextAAM += 1

        # Iterate through both reactants and products,
        # replacing corresponding aam atom with fragment
        for molecule in reactionInst.reactants + reactionInst.agents + reactionInst.products:
            for atom in molecule.atomList:
                if str(atom.aam) in fragmentsPseudo.keys():
                    molecule.replaceAtomWithMolecule(atom, fragmentsPseudo[str(atom.aam)])

        #print "Instance: \n" + str(reactionInst)

        reactionInst.finalize()

        return reactionInst


def sanitize_name(name):
    return re.sub(r'\W+', '', name).lower()

def sanitize_symbol(name):
    return re.sub(r'[^a-zA-Z0-9_-]+', '', name).lower()

def pseudoatomToList(string):
    #print "Unwrapping a symbol list " + string
    if string[0] == "[" and string[-1] == "]":
        #print "  success"
        return re.findall('(?:([a-zA-Z0-9-]+),?)', string[1:-1])
    else:
        #print "  failure"
        return [string]


def getInstanceByName(atom):
    """
        This method returns an actual instance of a pseudoatom.
    """
    #print "Getting instance of " + sanitize_symbol(atom.symbol)
    anchor_aam = atom.aam
    standard_name = sanitize_symbol(atom.symbol)
    build_function = PSEUDO[standard_name][0]
    args = PSEUDO[standard_name][1]

    return build_function(anchor_aam, args)

#def buildMethyl(anchorAAM, args):
#    return buildAlkyl(anchorAAM, {"size" : [1]})

def buildAlkyl(anchorAAM, args):
    """ Must return a molecule whose anchor is not None """

    # args["size"] is a list of integers
    # must select a size arbitrarily from list
    size = int(random.choice(args["size"]))

    if size < 1:
        raise Exception("Alkyl size cannot be less than one!")

    molecule = Molecule()
    root = Atom("C", 0, 0, 0, 0, 0)
    root.aam = anchorAAM
    molecule.addAtom(root)
    molecule.anchor = root

    if size == 100: # special case

        # Starting atom of the ring
        c1 = None

        # gamble on whether it's a phenyl or a benzyl
        if random.randint(0,1) == 0:
            # saturate root with hydrogens
            h1 = Atom("H", 0, 0, 0, 0, 0)
            h2 = Atom("H", 0, 0, 0, 0, 0)
            molecule.addAtom(h1, h2)
            molecule.addBond(Bond(0, 1, root, h1))
            molecule.addBond(Bond(0, 1, root, h2))
            # create a new atom as the ring starter
            c1 = Atom("C", 0, 0, 0, 0, 0)
            molecule.addAtom(c1)
            molecule.addBond(Bond(0, 1, root, c1))
        else:
            # otherwise, ring includes the root
            c1 = root

        # build a ring

        c2 = Atom("C", 0, 0, 0, 0, 0)
        c3 = Atom("C", 0, 0, 0, 0, 0)
        c4 = Atom("C", 0, 0, 0, 0, 0)
        c5 = Atom("C", 0, 0, 0, 0, 0)
        c6 = Atom("C", 0, 0, 0, 0, 0)
        molecule.addAtom(c2, c3, c4, c5, c6)
        molecule.addBond(Bond(0, 1, c1, c2))
        molecule.addBond(Bond(0, 2, c2, c3))
        molecule.addBond(Bond(0, 1, c3, c4))
        molecule.addBond(Bond(0, 2, c4, c5))
        molecule.addBond(Bond(0, 1, c5, c6))
        molecule.addBond(Bond(0, 2, c6, c1))

    else:   # arbitrary tree without rings

        (size1, size2, size3) = splitThreeWays(size - 1)

        buildAlkylTree(molecule, root, size1)
        buildAlkylTree(molecule, root, size2)
        buildAlkylTree(molecule, root, size3)

    return molecule

def buildAlkylTree(molecule, anchor, size) :
    if size < 1 :
        atom = Atom("H", 0, 0, 0, 0, 0)

        molecule.addAtom(atom)
        if anchor is not None:
            molecule.addBond(Bond(0, 1, anchor, atom))
    else : # assume size is non-negative
        # create new carbon
        atom = Atom("C", 0, 0, 0, 0, 0)

        molecule.addAtom(atom)
        # link it back to parent
        if anchor is not None:
            molecule.addBond(Bond(0, 1, anchor, atom))

        (size1, size2, size3) = splitThreeWays(size - 1)

        buildAlkylTree(molecule, atom, size1)
        buildAlkylTree(molecule, atom, size2)
        buildAlkylTree(molecule, atom, size3)


def splitThreeWays(number):
    a = random.random()
    b = random.random()
    c = random.random()
    whole = a + b + c
    coeff = number / whole
    resA = int(round(coeff * a))
    resB = int(round(coeff * b))
    resC = int(number - resA - resB)
    #print "Splitting " + str(number) + " yields " + str((resA,resB,resC))
    return (resA,resB,resC)



def buildHalogen(anchorAAM, args):
    #print "Invoked buildHalogen with args = " + str(args)
    symbol = random.choice(args["symbol"])

    molecule = Molecule()
    root = Atom(symbol, 0, 0, 0, 0, 0)
    root.aam = anchorAAM
    molecule.addAtom(root)
    molecule.anchor = root

    return molecule

def buildLindlarsCatalyst(anchorAAM, args):
    molecule = Molecule()
    root = Atom("Lindlar's catalyst", 0, 0, 0, 0, 0)
    root.aam = anchorAAM
    molecule.addAtom(root)
    molecule.anchor = root

    return molecule

def buildTosylate(anchorAAM, args):
    molecule = Molecule()
    root = Atom("Ts", 0, 0, 0, 0, 0)
    root.aam = anchorAAM
    molecule.addAtom(root)
    molecule.anchor = root
    oxygen = Atom("O", 0, 0, 0, 0, 0, {"CHG" : "-1"})
    molecule.addAtom(oxygen)
    molecule.addBond(Bond(0, 1, root, oxygen))

    return molecule

def buildBromineAnion(anchorAAM, args):
    molecule = Molecule()
    root = Atom("Br", 0, 0, 0, 0, 0, {"CHG" : "-1"})
    root.aam = anchorAAM
    molecule.addAtom(root)
    molecule.anchor = root

    return molecule

def buildIodineAnion(anchorAAM, args):
    molecule = Molecule()
    root = Atom("I", 0, 0, 0, 0, 0, {"CHG" : "-1"})
    root.aam = anchorAAM
    molecule.addAtom(root)
    molecule.anchor = root

    return molecule

def buildROH(anchorAAM, args):
    molecule = Molecule()
    root = Atom("smthng", 0, 0, 0, 0, 0)
    root.aam = anchorAAM
    molecule.addAtom(root)
    molecule.anchor = root
    oxygen = Atom("O", 0, 0, 0, 0, 0)
    hydrogen = Atom("H", 0, 0, 0, 0, 0)
    molecule.addAtom(oxygen)
    molecule.addAtom(hydrogen)
    molecule.addBond(Bond(0, 1, root, oxygen))
    molecule.addBond(Bond(0, 1, hydrogen, oxygen))
    return molecule

def buildAmmonia(anchorAAM, args):
    molecule = Molecule()
    root = Atom("N", 0, 0, 0, 0, 0)
    root.aam = anchorAAM
    molecule.addAtom(root)
    molecule.anchor = root
    h1 = Atom("H", 0, 0, 0, 0, 0)
    h2 = Atom("H", 0, 0, 0, 0, 0)
    h3 = Atom("H", 0, 0, 0, 0, 0)
    molecule.addAtom(h1)
    molecule.addAtom(h2)
    molecule.addAtom(h3)
    molecule.addBond(Bond(0, 1, root, h1))
    molecule.addBond(Bond(0, 1, root, h2))
    molecule.addBond(Bond(0, 1, root, h3))

    return molecule

def buildWater(anchorAAM, args):
    molecule = Molecule()
    root = Atom("O", 0, 0, 0, 0, 0)
    root.aam = anchorAAM
    molecule.addAtom(root)
    molecule.anchor = root
    h1 = Atom("H", 0, 0, 0, 0, 0)
    h2 = Atom("H", 0, 0, 0, 0, 0)
    molecule.addAtom(h1)
    molecule.addAtom(h2)
    molecule.addBond(Bond(0, 1, root, h1))
    molecule.addBond(Bond(0, 1, root, h2))

    return molecule

def buildAlkaliMetal(anchorAAM, args):
    # Not implemented
    return None


PSEUDO = {
        "alkyl" : (
                buildAlkyl,     # function that builds it
                { "size" : [1, 2, 3, 100] }     # arguments the function takes
            ),
        "halogen" : (buildHalogen, {}),
        "alkalimetal" : (buildAlkaliMetal, {}),
        "methyl" : (buildAlkyl, { "size" : [1] }),
        "lindlarscatalyst" : (buildLindlarsCatalyst, {}),
        "tso-" : (buildTosylate, {}),
        "nh3" : (buildAmmonia, {}),
        "i-" : (buildIodineAnion, {}),
        "h2o" : (buildWater, {}),
        "roh" : (buildROH, {}),
        "br-" : (buildBromineAnion, {}),
        "x" : (buildHalogen, { "symbol" : ["F", "Cl", "Br", "I"] }),
    }

ATOM_NAMES = {
        "H" : "hydrogen",
        "He" : "helium",
        "Li" : "lithium",
        "Be" : "beryllium",
        "B" : "boron",
        "C" : "carbon",
        "N" : "nitrogen",
        "O" : "oxygen",
        "F" : "fluorine",
        "Ne" : "neon",
        "Na" : "sodium",
        "Mg" : "magnesium",
        "Al" : "aluminium",
        "Si" : "silicon",
        "P" : "phosphorus",
        "S" : "sulphur",
        "Cl" : "chlorine",
        "Ar" : "argon",
        "K" : "potassium",
        "Ca" : "calcium",
        "Sc" : "scandium",
        "Ti" : "titanium",
        "V" : "vanadium",
        "Cr" : "chromium",
        "Mn" : "manganese",
        "Fe" : "iron",
        "Co" : "cobalt",
        "Ni" : "nickel",
        "Cu" : "copper",
        "Zn" : "zink",
        "Ga" : "gallium",
        "Ge" : "germanium",
        "As" : "arsenic",
        "Se" : "selenium",
        "Br" : "bromine",
        "Kr" : "krypton",
        "Rb" : "rubidium",
        "Sr" : "strontium",
        "Y" : "yttrium",
        "Zr" : "zirconium",
        "Nb" : "niobium",
        "Mo" : "molybdenum",
        "Tc" : "technetium",
        "Ru" : "ruthenium",
        "Rh" : "rhodium",
        "Pd" : "palladium",
        "Ag" : "silver",
        "Cd" : "cadmium",
        "In" : "indium",
        "Sn" : "tin",
        "Sb" : "antimony",
        "Te" : "tellurium",
        "I" : "iodine",
        "Xe" : "xenon",
        "Cs" : "caesium",
        "Ba" : "barium",
        # Omitting lanthanoids (57-71)
        "Hf" : "hafnium",
        "Ta" : "tantalum",
        "W" : "tungsten",
        "Re" : "rhenium",
        "Os" : "osmium",
        "Ir" : "iridium",
        "Pt" : "platinum",
        "Au" : "gold",
        "Hg" : "mercury",
        "Tl" : "thallium",
        "Pb" : "lead",
        "Bi" : "bismuth",
        "Po" : "polonium",
        "At" : "astatine",
        "Rn" : "radon",
        "Fr" : "francium",
        "Ra" : "radium"
        # Omitting 89-118+
    }

# THis is a hack
LIST_TRANSLATION = {
        "C" : "Methyl",
    }

# def getSubmolecule(mol, size):
#     """
#     Returns a submolecule of mol. Size of submolecule is parametrized. If there are not
#     enough molecules, returns the largest submolecule by stripping one atom from mol.
#     """
#     if size >= len(mol.atoms):
#         size = len(mol.atoms) - 1

#     startMol = copy.deepcopy(mol)

#     # start atom must be a leaf
#     startAtom = None
#     foundAnotherBondToIt = True
#     while foundAnotherBondToIt:
#         bond = random.choice(startMol.bonds)
#         startAtom = random.choice([bond.toAtom, bond.fromAtom])
#         # for all other bonds in molecule...
#         foundAnotherBondToIt = False
#         for b in startMol.bonds:
#             if b is not bond and (b.toAtom is atom or b.fromAtom is atom):
#                 foundAnotherBondToIt = True
#                 break

#     random.choice(tmpMol.atoms)
#     endMol = Molecule()

#     return getSubmRec(startMol, startAtom, size, endMol)

# def getSubmRec(mol, atom, size, latestMol):
#     if size == len(latestMol.atoms):
#         return latestMol
#     else:
#         # find the outgoing bond
#         for bond in mol.bonds:
#             if bond.fromAtom == atom and bond.toAtom not in latestMol.atoms:
#                 # store bond and atom it leads to, repeat for the latter
#                 latestMol.atoms.append(bond.toAtom)
#                 latestMol.bonds.append(bond)
#                 return getSubmRec(mol, bond.toAtom, size, latestMol)

#             elif bond.toAtom == atom and bond.fromAtom not in latestMol.atoms:
#                 latestMol.atoms.append(bond.fromAtom)
#                 latestMol.bonds.append(bond)
#                 latest
#                 return getSubmRec(mol, bond.fromAtom, size, latestMol)

def mutate_cross(mol1, mol2):

    pass

def mutateMolecules(molecules, number=0):
    """
    This shall take a list of molecules and return a new list of new molecules
    derived from the original ones. Also takes the length of the return list as a parameter.
    """

    # Ideas:
    # 1. Take one molecule, break an arbitrary bond and put hydrogens on both ends, yielding two molecules
    # 2. Take two molecules, find a hydrogen in both, remove them, connect two molecules into one
    # 3. Take one molecule, find two bonds, swap fragments at end of each bond (requires structure recognition)
    # 4. Take two molecules, pick a bond in each, swap fragments

    result = []

    # By default, return as many as given
    if number == 0:
        number = len(molecules)

    for i in range(0, number):

        # 4
        mol1 = copy.deepcopy(random.choice(molecules))
        mol2 = copy.deepcopy(random.choice(molecules))
        random.shuffle(mol1.bondList)
        random.shuffle(mol2.bondList)
        b1 = None
        b2 = None
        order = random.choice([1,2])
        for b in mol1.bondList:
            if b.order == order:
                b1 = b
                break
        for b in mol2.bondList:
            if b.order == order:
                b2 = b
                break
        if b1 is None or b2 is None:
            continue
        # swap fragments
        tmp = b1.fromAtom
        b1.fromAtom = b2.fromAtom
        b2.fromAtom = tmp

        # put atoms in order in each molecule
        mol1.inferAtomsFromBonds()
        mol2.inferAtomsFromBonds()

        print "Added two bastards:"
        print str(mol1)
        print str(mol2)
        result.append(mol1)
        result.append(mol2) # Note: this loop will yield twice as many molecules as given

    return result[:number] # cut off the excess; inefficient
