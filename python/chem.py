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
        self.anchor = None  # Obsolete
        self.anchors = None # Replaces self.anchor, because R-groups can have multiple anchors
        self.owner = None   # For debugging only, set this to the reaction object the molecule belongs to

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
            raise Exception("New molecule does not have an anchor!\n(Reaction is " + self.owner.name + ")")

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


    def __eq__(self, other):
        """
            Let's agree that two Molecule objects are equal if and only if
            they represent the same chemical structure, regardless of the object's innards.
            The way 'draw' is implemented, the AAM are be ignored, but stereo is preserved.
        """
        if isinstance(other, self.__class__):
            import draw
            (i, _) = draw.get_indigo()
            imol1 = draw.build_indigo_molecule(self, i)
            imol2 = draw.build_indigo_molecule(other, i)
            #print imol1.canonicalSmiles(), "versus", imol2.canonicalSmiles()
            return imol1.canonicalSmiles() == imol2.canonicalSmiles()
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)


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
        molecule.owner = self

    def addAgent(self, molecule):
        self.agents.append(molecule)
        molecule.owner = self

    def addProduct(self, molecule):
        self.products.append(molecule)
        molecule.owner = self

    def addRGroup(self, rgroupNumber, molecule):
        rgroupName = "R" + str(rgroupNumber)
        if rgroupName not in self.rgroups:
            self.rgroups[rgroupName] = []
        self.rgroups[rgroupName].append(molecule)
        molecule.owner = self

    def finalize(self):
        """ Merely a sanity check
        Only execute after everything has been added to reaction.
        """
        print "=" * 20, "Sanity check for reaction", self.name, "=" * 20
        # Test AAM within and across agent groups
        aamReactants = []
        aamAgents = []
        aamProducts = []

        for mol in self.reactants:
            for atom in mol.atomList:
                #print "Sanity: " + str(atom)
                if atom.aam == 0:
                    raise Exception("Sanity check: reaction " + self.name + " contains a reactant atom with AAM = 0")
                if atom.aam in aamReactants:
                    raise Exception("Sanity check: reaction " + self.name + " contains two reactant atoms with the same AAM, #" + str(atom.aam) + ";\n current atom: " + str(atom))
                else:
                    aamReactants.append(atom.aam)

        for mol in self.agents:
            for atom in mol.atomList:
                if atom.aam == 0:
                    raise Exception("Sanity check: reaction " + self.name + " contains a catalyst atom with AAM = 0")
                if atom.aam in aamAgents:
                    raise Exception("Sanity check: reaction " + self.name + " contains two catalyst atoms with the same AAM, #" + str(atom.aam) + ";\n current atom: " + str(atom))
                else:
                    aamAgents.append(atom.aam)

        for mol in self.products:
            for atom in mol.atomList:
                if atom.aam == 0:
                    raise Exception("Sanity check: reaction " + self.name + " contains a product atom with AAM = 0")
                if atom.aam in aamProducts:
                    raise Exception("Sanity check: reaction " + self.name + " contains two product atoms with the same AAM, #" + str(atom.aam) + ";\n current atom: " + str(atom))
                else:
                    aamProducts.append(atom.aam)

        # Test atom counts between reactants and products
        if len(set(aamReactants).intersection(set(aamProducts))) != len(aamReactants):
            message = ("Reaction: " + str(self.name) +
                      "\nReactant aam: " + str(sorted(aamReactants)) +
                      "\n Product aam: " + str(sorted(aamProducts)) +
                      "\nReactants: " + "\n\n".join([str(r) for r in self.reactants]) +
                      "\nProducts: " + "\n\n".join([str(r) for r in self.products]))
            raise Exception("Sanity check: mismatch between reactant and product atom sets!\n" + message)

        # Test whether AAM are balanced
        if len(set(aamReactants).intersection(set(aamAgents))) != 0:
            raise Exception("Sanity check: reactants and catalyst share some atoms in " + self.name)

        # Count atoms by objects and by aam
        if self.numberOfAtomsOverall != len(aamReactants + aamAgents):
            raise Exception("Sanity check: self.numberOfAtomsOverall != len(aamReactants + aamAgents) in " + self.name)

        print "All numbers check out."

        # We want to be sure that this reaction can be instantiated
        # Test for unknown pseudoatoms
        def test_a_list_of_symbols(symbols):
            for symbol in symbols:
                if symbol not in ATOM_NAMES and sanitize_symbol(symbol) not in PSEUDO.keys() and symbol not in self.rgroups:
                    if symbol[0] != "[":
                        raise Exception("Unrecognized atom name - '" + symbol + "', or '" + sanitize_symbol(symbol) + "' - in reaction " + self.name)
                    else:
                        test_a_list_of_symbols(pseudoatomToList(symbol))

        import itertools
        all_rgroup_mols = list(itertools.chain.from_iterable(self.rgroups.values()))
        for mol in self.reactants + self.agents + self.products + all_rgroup_mols:
            test_a_list_of_symbols([a.symbol for a in mol.atomList])

        # Test R-groups
        for rname, rmollist in self.rgroups.iteritems():
            for rmol in rmollist:
                if rmol.anchors is None:
                    raise Exception("R-group " + rname + "'s choice " + str(rmol) + " has no attachment points at all!")
                if len(rmol.anchors) > 1:
                    print "One of the R-group " + rname + "'s choices has " + str(len(rmol.anchors)) + " attachment points, please investigate."

        print "-" * 50

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

        reactionInst.finalize()  # REMOVE THIS WHEN IN PRODUCTION; way too expensive

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

def buildPseudoatom(anchorAAM, args):
    molecule = Molecule()
    root = Atom(args["symbol"], 0, 0, 0, 0, 0)
    root.aam = anchorAAM
    molecule.addAtom(root)
    molecule.anchor = root

    return molecule


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
        "pdc" : (buildPseudoatom, { "symbol" : "Pd/C"}),
        "alkynyl" : (buildPseudoatom, { "symbol" : "TODO: Alkynyl"}),
        "carboaryl" : (buildPseudoatom, { "symbol" : "TODO: Carboaryl"}),
        "alkenyl" : (buildPseudoatom, { "symbol" : "TODO: Alkenyl"}),
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
#
# def mutate_cross(mol1, mol2):
#
#     pass
#
# def mutateMolecules(molecules, number=0):
#     """
#     This shall take a list of molecules and return a new list of new molecules
#     derived from the original ones. Also takes the length of the return list as a parameter.
#     """
#
#     # Ideas:
#     # 1. Take one molecule, break an arbitrary bond and put hydrogens on both ends, yielding two molecules
#     # 2. Take two molecules, find a hydrogen in both, remove them, connect two molecules into one
#     # 3. Take one molecule, find two bonds, swap fragments at end of each bond (requires structure recognition)
#     # 4. Take two molecules, pick a bond in each, swap fragments
#
#     result = []
#
#     # By default, return as many as given
#     if number == 0:
#         number = len(molecules)
#
#     for i in range(0, number):
#
#         # 4
#         mol1 = copy.deepcopy(random.choice(molecules))
#         mol2 = copy.deepcopy(random.choice(molecules))
#         random.shuffle(mol1.bondList)
#         random.shuffle(mol2.bondList)
#         b1 = None
#         b2 = None
#         order = random.choice([1,2])
#         for b in mol1.bondList:
#             if b.order == order:
#                 b1 = b
#                 break
#         for b in mol2.bondList:
#             if b.order == order:
#                 b2 = b
#                 break
#         if b1 is None or b2 is None:
#             continue
#         # swap fragments
#         tmp = b1.fromAtom
#         b1.fromAtom = b2.fromAtom
#         b2.fromAtom = tmp
#
#         # put atoms in order in each molecule
#         mol1.inferAtomsFromBonds()
#         mol2.inferAtomsFromBonds()
#
#         print "Added two bastards:"
#         print str(mol1)
#         print str(mol2)
#         result.append(mol1)
#         result.append(mol2) # Note: this loop will yield twice as many molecules as given
#
#     return result[:number] # cut off the excess; inefficient
#
#
# class bastardReaction:
#     '''
#     The bastardReaction class is to create wrong answers for questions.
#     The bastardReaction class will require both the reactant and product to produce incorrect molecules
#
#     The max number of choices provided to the student will be max to 8 subtracted the correct choices. Each choice will be a molecule
#
#     What is the best way to organize this
#     From the conditions provided by the chem prof there will be a requirement to find atoms that are candidates
#
#     '''
#     _reactant = []
#     _product = []
#
#     _reactant_bonds_order_change = []
#     _product_bonds_order_change = []
#
#     _reactant_bonds_disappeared = []
#     _reactant_bonds_appeared = []
#
#     _product_bonds_disappeared = []
#     _product_bonds_appeared = []
#
#     _reactant_charges_changed = []
#     _product_charges_changed = []
#
#     _reactant_moved_atoms = []
#     _product_moved_atoms = []
#
#     def __init__(self, reactant, product):
#
#         # set reactant and product
#         self._reactant = reactant
#         self._product = product
#
#         # List of bond orders that have changed
#         self._reactant_bonds_order_change = []
#         self._product_bonds_order_change = []
#
#         # store the reactant's bonds that have appeared or disappeared
#         self._reactant_bonds_disappeared = []
#         self._reactant_bonds_appeared = []
#
#         # store the product's bond that have appea
#         self._product_bonds_disappeared = []
#         self._product_bonds_appeared = []
#
#         # list of atom charged that have been changed
#         self._reactant_charges_changed = []
#         self._product_charges_changed = []
#
#         # Store Bonds that have appeared and disappeared
#         self.set_bonds_appeared_and_disapeared()
#
#         # Store bonds orders that have changed
#         self.set_bonds_order_changed()
#
#         # Store atoms which charges have changed
#         self.set_atom_charges_changed()
#
#         # Store Atoms that have moved to other molecules
#         self.store_atoms_moved()
#
#         # Atoms moved
#         self._atoms_moved_to_product
#         self._atoms_moved_to_reactant
#
#         self.store_atoms_moved()
#
#         print "################################ Product Charges Changed         ################################"
#         for atom in self._product_charges_changed:
#             print str(atom)
#
#         # All bonds that appeared
#         print "################################ Product order changed ################################"
#         for product_bond in self._product_bonds_order_change:
#             print str(product_bond)
#
#         # All bonds that appeared
#         print "################################ Product appear Bonds Appeared   ################################"
#         for product_bond in self._product_bonds_appeared:
#             print str(product_bond)
#
#         print "################################ Product disappear bonds         ################################"
#         for product_bond in self._product_bonds_disappeared:
#             print str(product_bond)
#
#         print "################################ Reactant Charges Changed         ################################"
#         for atom in self._reactant_charges_changed:
#             print str(atom)
#
#         # All bonds that appeared
#         print "################################ Reactant order changed ################################"
#         for product_bond in self._reactant_bonds_order_change:
#             print str(product_bond)
#
#         # All bonds that appeared
#         print "################################ Reactant appear Bonds Appeared   ################################"
#         for product_bond in self._reactant_bonds_appeared:
#             print str(product_bond)
#
#         print "################################ Reactant disappear bonds         ################################"
#         for product_bond in self._reactant_bonds_disappeared:
#             print str(product_bond)
#
#     	print "################################ Reactant Molecules              #################################"
#         for molecule in reactant:
#             print molecule.__str__()
#
#         print "################################ Product Molecules               ################################"
#     	for molecule in product:
#             print molecule.__str__()
#
#
#     def store_atoms_moved(self):
#
#         atoms_moved_to_product = []
#         atoms_moved_to_reactant = []
#
#         # Retrieve candidates of atoms that have moved
#         for reactant_bond_disappeared in self._reactant_bonds_disappeared:
#             # get the bonds from and to atoms and add them to atoms_moved_to_reactant
#             atoms_moved_to_reactant.append(reactant_bond_disappeared.fromAtom)
#             atoms_moved_to_reactant.append(reactant_bond_disappeared.toAtom)
#
#         for product_bond_disappeared in self._product_bonds_disappeared:
#         # get the bonds from and to atoms and add them to atoms_moved_to_reactant
#             atoms_moved_to_product.append(product_bond_disappeared.fromAtom)
#             atoms_moved_to_product.append(product_bond_disappeared.toAtom)
#
#         # We now have the atoms that could be candidates that have been moved, but we need to figure out from which Molecule that atom moved from
#
#         for index, reactant_molecule in enumerate(self._reactant):
#             for atom in atoms_moved_to_product:
#                 if atom in reactant_molecule.atomList and index < len(self._product):
#                     if atom in self._product[index].atomList:
#                         atoms_moved_to_product.remove(atom)
#
#         self._atoms_moved_to_product = atoms_moved_to_product
#
#         # Print the results
#         print "################################################## atoms_moved_to_product  ##################################################"
#
#         for atom in self._atoms_moved_to_product:
#             print str(atom)
#
#         for index, product_molecule in enumerate(self._product):
#             for atom in atoms_moved_to_reactant:
#                 if atom in product_molecule.atomList and index < len(self._reactant):
#
#                     if atom in self._reactant[index].atomList:
#                         atoms_moved_to_reactant.remove(atom)
#
#         self._atoms_moved_to_reactant = atoms_moved_to_reactant
#
#         print "################################################## atoms_moved_to_reactant  ##################################################"
#         for atom in self._atoms_moved_to_reactant:
#             print str(atom)
#
#     def set_atom_charges_changed(self):
#         # candidate for charge changes
#         reactant_atoms = []
#         product_atoms = []
#
#         for molecule in self._reactant:
#             reactant_atoms.extend(molecule.atomList)
#
#         for molecule in self._product:
#             product_atoms.extend(molecule.atomList)
#
#         for atom in reactant_atoms:
#             if 'CHG' in atom.attribs.keys():
#                 self._reactant_charges_changed.append(atom)
#
#         for atom in product_atoms:
#             if 'CHG' in atom.attribs.keys():
#                 self._product_charges_changed.append(atom)
#
#     def set_bonds_order_changed(self):
#
#         # temp List of bonds
#         reactant_bonds = []
#         product_bonds = []
#         product2_bonds = []
#
#         # add all bonds to temporary bond list
#         for molecule in self._reactant:
#             reactant_bonds.extend(molecule.bondList)
#
#         for molecule in self._product:
#             product_bonds.extend(molecule.bondList)
#             product2_bonds.extend(molecule.bondList)
#
#         # set _product_bonds_order_change
#         for reactant_bond in reactant_bonds:
#             for product_bond in product_bonds:
#                 if reactant_bond.__eq__(product_bond):
#                     product_bonds.remove(product_bond)
#
#         for product_bond_appeared in self._product_bonds_appeared:
#             for product_bond in product_bonds:
#                 if product_bond_appeared.__eq__(product_bond):
#                     product_bonds.remove(product_bond)
#
#         self._product_bonds_order_change = product_bonds
#
#         #set _reactant_bonds_order_change
#         for product_bond in product2_bonds:
#             for reactant_bond in reactant_bonds:
#                 if product_bond.__eq__(reactant_bond):
#                     reactant_bonds.remove(reactant_bond)
#
#         for reactant_bond_appeared in self._reactant_bonds_appeared:
#             for reactant_bond in reactant_bonds:
#                 if reactant_bond_appeared.__eq__(reactant_bond):
#                     reactant_bonds.remove(reactant_bond)
#
#         self._reactant_bonds_order_change = reactant_bonds
#
#     def set_bonds_appeared_and_disapeared(self):
#
#         # temp List of bonds
#         reactant_bonds = []
#         product_bonds = []
#         product2_bonds = []
#
#         # add all bonds to temporary bond list
#         for molecule in self._reactant:
#             reactant_bonds.extend(molecule.bondList)
#
#         for molecule in self._product:
#             product_bonds.extend(molecule.bondList)
#             product2_bonds.extend(molecule.bondList)
#
#         # set _product_bonds_appeared and _reactant_bonds_disappeared
#         for reactant_bond in reactant_bonds:
#             for product_bond in product_bonds:
#                 if ((reactant_bond.fromAtom == product_bond.fromAtom and reactant_bond.toAtom == product_bond.toAtom) or (reactant_bond.fromAtom == product_bond.toAtom and reactant_bond.toAtom == product_bond.fromAtom)):
#                     product_bonds.remove(product_bond)
#
#         self._product_bonds_appeared = product_bonds
#         self._reactant_bonds_disappeared = product_bonds
#
#         #set _reactant_bonds_appeared and _product_bonds_disappeared
#         for product_bond in product2_bonds:
#             for reactant_bond in reactant_bonds:
#                 if ((product_bond.fromAtom == reactant_bond.fromAtom and product_bond.toAtom == reactant_bond.toAtom) or (product_bond.fromAtom == reactant_bond.toAtom and product_bond.toAtom == reactant_bond.fromAtom)):
#                     reactant_bonds.remove(reactant_bond)
#
#         self._reactant_bonds_appeared = reactant_bonds
#         self._product_bonds_disappeared = reactant_bonds
#
#
#     def newmutateMolecules(self, molecule):
#
#         # Conditions:
#
#         # 3. if there is a main atom which is not a C or H then give it extra bonds or remove some
#
#         # 4. When there is a H with a other atom remove the H and add a bond, because a H has one outer electron replacing it with a bond will make it seem correct.
#             # This should require to know what happen in the previous reaction.
#
#
#             # This will require to look at the difference between the reactant and product.
#
#         pass
#
#     # 1. if there is a charge in one of the Atoms remove it or flip it
#     # This Condition doesn't require any graph structure to be acomplished. All is required is the molcule
#     def mutate_charges(self, molecules, charges_changed ):
#
#         results = []
#         for molecule in molecules:
#             # we get the product charges
#             for atom_charge in charges_changed:
#                 # and for every charged atom check if it's in the particular molecule
#                 for atom in molecule.atomList:
#                     if atom_charge.__eq__(atom):
#                         # if atom has a negative change it to pos or remove
#                         if atom_charge.attribs['CHG'] == '-1':
#                             # choose Randomly if charge will be flipped or deleted
#                             if bool(random.getrandbits(1)):
#                                 atom.attribs['CHG'] = '1'
#                                 results.append(copy.deepcopy(molecule))
#                                 # return attribute to it's original state
#                                 atom.attribs['CHG'] = '-1'
#                             else:
#                                 del atom.attribs['CHG']
#                                 results.append(copy.deepcopy(molecule))
#                                 # return attribute to it's original state
#                                 atom.attribs.update({'CHG': '-1'})
#                         # atom has a positive charge flip it or remove
#                         elif atom_charge.attribs['CHG'] == '1':
#                             if bool(random.getrandbits(1)):
#                                 atom.attribs['CHG'] = '-1'
#                                 results.append(copy.deepcopy(molecule))
#                                 # return attribute to it's original state
#                                 atom.attribs['CHG'] = '1'
#                             else:
#                                 del atom.attribs['CHG']
#                                 results.append(copy.deepcopy(molecule))
#                                 # return attribute to it's original state
#                                 atom.attribs.update({'CHG' : '1' })
#         return results
#
#
#     def expand_molecule(self, molecules, order_bonds_changed ):
#
#         # if charges change size is zero then pass this strategy
#
#         results = []
#
#         # get the max aam number Note: the length of the list does not give you the max aam number
#         reaction_aam_count = 0
#         for molecule in molecules:
#             #print str(molecule.numberOfAtoms())
#             for atom in molecule.atomList:
#                 if atom.aam > reaction_aam_count:
#                     reaction_aam_count = atom.aam
#         reaction_aam_count = 1 + reaction_aam_count
#
#         molecules_copy = copy.deepcopy(molecules)
#         for molecule in molecules_copy:
#             for order_bond_changed in order_bonds_changed:
#                 for bond in molecule.bondList:
#                     if order_bond_changed.__eq__(bond):
#
#                         atom = Atom('C', 0,0,0,0, 0,{},reaction_aam_count )
#                         new_bond = Bond( 0, 1, atom,  bond.toAtom ,{})
#                         previous_bond = Bond( 0, bond.order, bond.fromAtom,  atom ,{})
#
#                         reaction_aam_count = reaction_aam_count + 1
#
#                         temp_molecule = copy.deepcopy(molecule)
#                         temp_molecule.bondList.remove(bond)
#                         temp_molecule.addAtom(atom)
#                         temp_molecule.addBond(new_bond)
#                         temp_molecule.addBond(previous_bond)
#
#                         results.append(temp_molecule)
#
#                         # if the bond is other then 2
#                         if bond.order == 2:
#                             temp_molecule_second_option = copy.deepcopy(molecule)
#
#                             atom = Atom('C', 0,0,0,0, 0,{},reaction_aam_count )
#                             new_bond = Bond( 0, bond.order, atom,  bond.toAtom ,{})
#                             previous_bond = Bond( 0, 1, bond.fromAtom,  atom ,{})
#
#                             temp_molecule_second_option.bondList.remove(bond)
#                             temp_molecule_second_option.addAtom(atom)
#                             temp_molecule_second_option.addBond(new_bond)
#                             temp_molecule_second_option.addBond(previous_bond)
#
#                             results.append(temp_molecule_second_option)
#
#
#
#         return results
#
#
#     # 2. if there is a bond conecting a molcule remove the atom and connect it with a bond.
#     # Number 2 will requies two see the changes between the reactant and product to figure out which atom is the best candidate. Further Research must be done to see how to make this good
#     def contract_molecule(self):
#         pass
#
#     def mutate_bond_order(self, molecules, candidate_bonds):
#
#         results = []
#
#         # TODO Create a condition that doesn't allow H atoms to not contain more then one bond
#
#         for molecule in molecules:
#             for candidate_bond in candidate_bonds:
#                     # get the molecule bonds
#                     for bond in molecule.bondList:
#                         # find the bond that has appeared
#                         if  candidate_bond.__eq__(bond):
#                             if bond.order == 2:
#                                 bond.order -= 1
#                                 results.append(copy.deepcopy(molecule))
#                                 bond.order +=1
#                             elif bond.order == 1:
#                                 bond.order += 1
#                                 results.append(copy.deepcopy(molecule))
#                                 bond.order -= 1
#                             elif bond.order == 3:
#                                 bond.order = 1
#                                 results.append(copy.deepcopy(molecule))
#                                 bond.order = 2
#                                 results.append(copy.deepcopy(molecule))
#                                 bond.order = 3
#
#         return results
#
#
#     def remove_particular_atom(self):
#         pass
#
#     # 5. swap a main atom with another also make sure they have been moved from the pervious reaction . A main atom would not be a C
#     def flip_particular_atoms(self):
#         pass
#
#     def formal_charge(self, atom, molecule):
#
#         pass
#
#
#     def get_atom_bonds(self, atom, molecule):
#
#         bonds = []
#
#         for bond in molecule.bondList:
#             if bond.toAtom.__eq__(atom):
#                 bonds.append(bond)
#             elif bond.fromAtom.__eq__(atom):
#                 bonds.append(bond)
#
#         return bonds
#
#     def return_atoms_moved(self, molecules, bonds_disappeared, atoms_moved ):
#
#         results = []
#
#         # for each atom moved find it's bond
#         for atom_moved in atoms_moved:
#             for bond_disappeared in bonds_disappeared:
#                 if bond_disappeared.fromAtom.__eq__(atom_moved):
#                     molecules_copy = copy.deepcopy(molecules)
#                     for molecule in molecules_copy:
#                         if bond_disappeared.toAtom in molecule.atomList:
#
#                             # we want to check if adding back this atom will cause any problems to the molecule
#                             from_atom_bonds = self.get_atom_bonds(bond_disappeared.toAtom, copy.deepcopy(molecule))
#
#                             #  if any of these bond have a order > 1 then reduce them
#                             bonds_order_greater_then_one = []
#                             for from_atom_bond in from_atom_bonds:
#                                 if from_atom_bond.order > 1:
#                                     bonds_order_greater_then_one.append(from_atom_bond)
#                             print str(bond_disappeared.fromAtom)
#                             print "#################################### bonds_order_greater_then_one ##########################################"
#                             for bond in bonds_order_greater_then_one:
#                                 print str(bond)
#
#                             if bond_disappeared.order == 1 and bond_disappeared.toAtom.symbol != 'H' and bond_disappeared.fromAtom.symbol != 'H':
#
#                                 molecule_copy = copy.deepcopy(molecule)
#                                 if len(bonds_order_greater_then_one) > 0 and bonds_order_greater_then_one[0] in molecule_copy.bondList:
#
#                                     molecule_copy.bondList.remove(bonds_order_greater_then_one[0])
#                                     bonds_order_greater_then_one[0].order = 1
#                                     molecule_copy.bindList.append(bonds_order_greater_then_one[0])
#                                     bond_copy = copy.deepcopy(bond_disappeared)
#                                     bond_copy.order = 2
#                                     molecule_copy.addBond(bond_copy)
#                                     molecule_copy.addAtom(atom_moved)
#                                     results.append(molecule_copy)
#
#
#                             # molecule_copy = copy.deepcopy(molecule)
#                             # bond_copy = copy.deepcopy(bond_disappeared)
#                             # molecule_copy.addBond(bond_copy)
#                             # molecule_copy.addAtom(atom_moved)
#                             # results.append(molecule_copy)
#
#
#                 elif bond_disappeared.toAtom.__eq__(atom_moved):
#
#                     molecules_copy = copy.deepcopy(molecules)
#                     for molecule in molecules_copy:
#                         if bond_disappeared.fromAtom in molecule.atomList:
#
#                             # we want to check if adding back this atom will cause any problems to the molecule
#                             to_atom_bonds = self.get_atom_bonds(bond_disappeared.fromAtom, copy.deepcopy(molecule))
#
#                             bonds_order_greater_then_one = []
#                             for to_atom_bond in to_atom_bonds:
#                                 if to_atom_bond.order > 1:
#                                     bonds_order_greater_then_one.append(to_atom_bond)
#
#                             # print str(bond_disappeared.toAtom)
#                             # print "#################################### bonds_order_greater_then_one ##########################################"
#                             # for bond in bonds_order_greater_then_one:
#                             #     print str(bond)
#
#                             if bond_disappeared.order == 1 and bond_disappeared.toAtom.symbol != 'H' and bond_disappeared.fromAtom.symbol != 'H':
#
#                                 molecule_copy = copy.deepcopy(molecule)
#                                 if len(bonds_order_greater_then_one) > 0 and bonds_order_greater_then_one[0] in molecule_copy.bondList:
#
#                                     molecule_copy.bondList.remove(bonds_order_greater_then_one[0])
#                                     bonds_order_greater_then_one[0].order = 1
#                                     molecule_copy.bondList.append(bonds_order_greater_then_one[0])
#                                     bond_copy = copy.deepcopy(bond_disappeared)
#                                     bond_copy.order = 2
#                                     molecule_copy.addBond(bond_copy)
#                                     molecule_copy.addAtom(atom_moved)
#                                     results.append(molecule_copy)
#
#                                     # molecule_copy.bondList.remove(bonds_order_greater_then_one[0])
#                                     # bonds_order_greater_then_one[0].order = 2
#                                     # molecule_copy.bondList.append(bonds_order_greater_then_one[0])
#
#
#                             molecule_copy = copy.deepcopy(molecule)
#                             bond_copy = copy.deepcopy(bond_disappeared)
#                             molecule_copy.addBond(bond_copy)
#                             molecule_copy.addAtom(atom_moved)
#                             results.append(molecule_copy)
#         return results
#
#     def mutateMolecules(self, molecules, number=0):
#
#         results = []
#         # molecule is a product it will require other atom and bond candidates
#         if molecules.__eq__(self._product):
#
#             #results.extend(self.mutate_charges( molecules, self._product_charges_changed ))
#             results.extend(self.expand_molecule(molecules, self._product_bonds_order_change))
#             #results.extend(self.expand_molecule(molecules, self._product_bonds_appeared))
#             results.extend(self.return_atoms_moved(molecules, self._product_bonds_disappeared, self._atoms_moved_to_product))
#             results.extend(self.mutate_bond_order(molecules, self._product_bonds_order_change))
#
#             # Current code below works really well for E1 reaction using sulfuric acid
#             # results.extend(self.expand_molecule(molecules, self._product_bonds_order_change))
#             # results.extend(self.expand_molecule(molecules, self._product_bonds_appeared))
#             # results.extend(self.return_atoms_moved(molecules, self._product_bonds_disappeared, self._atoms_moved_to_product))
#             # results.extend(self.mutate_bond_order(molecules, self._product_bonds_order_change))
#
#
#         elif molecules.__eq__(self._reactant):
#
#             #results.extend(self.mutate_charges( molecules, self._reactant_charges_changed ))
#             #results.extend(self.return_atoms_moved(molecules, self._reactant_bonds_disappeared, self._atoms_moved_to_reactant))
#
#             results.extend(self.expand_molecule(molecules, self._reactant_bonds_order_change))
#             results.extend(self.expand_molecule(molecules, self._reactant_bonds_appeared))
#             results.extend(self.mutate_bond_order(molecules, self._reactant_bonds_order_change))
#
#             # Current code below works really well for E1 reaction using sulfuric acid
#             # results.extend(self.expand_molecule(molecules, self._reactant_bonds_order_change))
#             # results.extend(self.expand_molecule(molecules, self._reactant_bonds_appeared))
#             # results.extend(self.mutate_bond_order(molecules, self._reactant_bonds_order_change))
#
#
#         # remove any molecules that have been generated correctly
#         for molecule in molecules:
#             for result in results:
#                 if molecule.__eq__(result):
#                     results.remove(result)
#
#
#         return results
