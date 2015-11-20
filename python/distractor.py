import copy
import random
import re
import chem


ATOM_VALENCE = {
        "H"  : 1,
        "He" : 2,
        "Li" : 1,
        "Be" : 2,
        "B"  : 3,
        "C"  : 4,
        "N"  : 5,
        "O"  : 6,
        "F"  : 7,
        "Ne" : 8,
        "Na" : 1,
        "Mg" : 2,
        "Al" : 3,
        "Si" : 4,
        "P"  : 6,
        "S"  : 6,
        "Cl" : 7,
        "Ar" : 8,
        "K"  : 1,
        "Ca" : 2,
        "Sc" : 2,
        "Ti" : 2,
        "V"  : 5,
        "Cr" : 1,
        "Mn" : 2,
        "Fe" : 2,
        "Co" : 2,
        "Ni" : 2,
        "Cu" : 1,
        "Zn" : 2,
        "Ga" : 3,
        "Ge" : 4,
        "As" : 5,
        "Se" : 6,
        "Br" : 7,
        "Kr" : 8,
        "Rb" : 1,
        "Sr" : 2,
        "Y"  : 2,
        "Zr" : 2,
        "Nb" : 1,
        "Mo" : 1,
        "Tc" : 2,
        "Ru" : 1,
        "Rh" : 1,
        "Pd" : 18, # What is the valence why is it 10. i looked online and it says 8 is like the max valence number
        "Ag" : 1,
        "Cd" : 2,
        "In" : 3,
        "Sn" : 4,
        "Sb" : 5,
        "Te" : 6,
        "I"  : 7,
        "Xe" : 8,
        "Cs" : 1,
        "Ba" : 2,
        "Lu" : 2, # Omitting lanthanoids (57-71)
        "Hf" : 2,
        "Ta" : 2,
        "W"  : 2,
        "Re" : 2,
        "Os" : 2,
        "Ir" : 2,
        "Pt" : 1,
        "Au" : 1,
        "Hg" : 2,
        "Tl" : 3,
        "Pb" : 4,
        "Bi" : 5,
        "Po" : 6,
        "At" : 7,
        "Rn" : 8,
        "Fr" : 1,
        "Ra" : 2,
}


class DistractorReaction:
    """
    Mutates a multiple choice molecule to a distractor
    """

    _reactant = []
    _product = []

    _reactant_bonds_order_change = []
    _product_bonds_order_change = []

    _reactant_bonds_disappeared = []
    _reactant_bonds_appeared = []

    _product_bonds_disappeared = []
    _product_bonds_appeared = []

    _reactant_charges_changed = []
    _product_charges_changed = []

    _reactant_moved_atoms = []
    _product_moved_atoms = []

    def __init__(self, reactant, product):

        # Store reactant and product
        self._reactant = reactant
        self._product = product

        # List of bond orders that have changed
        self._reactant_bonds_order_change = []
        self._product_bonds_order_change = []

        # store the reactant's bonds that have appeared or disappeared
        self._reactant_bonds_disappeared = []
        self._reactant_bonds_appeared = []

        # store the product's bond that have appea
        self._product_bonds_disappeared = []
        self._product_bonds_appeared = []

        # list of atom charged that have been changed
        self._reactant_charges_changed = []
        self._product_charges_changed = []

        # List of Atoms moved
        self._atoms_moved_to_product = []
        self._atoms_moved_to_reactant = []

        # Store Bonds that have appeared and disappeared
        self.store_bonds_appeared_and_disapeared()

        # Store bonds orders that have changed
        self.store_bonds_order_changed()

        # Store atoms which charges have changed
        self.store_atoms_charge_changed()

        # Store Atoms that have moved to other molecules
        self.store_atoms_moved()

        # store atoms that have moved to other molecules
        self.store_atoms_moved()

    def store_atoms_moved(self):
        """
        Compares both Reactant and Product and stores the atoms that have moved
        """

        atoms_moved_to_product = []
        atoms_moved_to_reactant = []

        # Retrieve candidates of atoms that have moved
        for reactant_bond_disappeared in self._reactant_bonds_disappeared:
            # get the bonds from and to atoms and add them to atoms_moved_to_reactant
            atoms_moved_to_reactant.append(reactant_bond_disappeared.fromAtom)
            atoms_moved_to_reactant.append(reactant_bond_disappeared.toAtom)

        for product_bond_disappeared in self._product_bonds_disappeared:
        # get the bonds from and to atoms and add them to atoms_moved_to_reactant
            atoms_moved_to_product.append(product_bond_disappeared.fromAtom)
            atoms_moved_to_product.append(product_bond_disappeared.toAtom)

        # We now have the atoms that could be candidates that have been moved, but we need to figure out from which Molecule that atom moved from

        for index, reactant_molecule in enumerate(self._reactant):
            for atom in atoms_moved_to_product:
                if atom in reactant_molecule.atomList and index < len(self._product):
                    if atom in self._product[index].atomList:
                        atoms_moved_to_product.remove(atom)

        self._atoms_moved_to_product = atoms_moved_to_product


        for index, product_molecule in enumerate(self._product):
            for atom in atoms_moved_to_reactant:
                if atom in product_molecule.atomList and index < len(self._reactant):

                    if atom in self._reactant[index].atomList:
                        atoms_moved_to_reactant.remove(atom)

        self._atoms_moved_to_reactant = atoms_moved_to_reactant


    def store_atoms_charge_changed(self):
        """
        Compares both Reactant and Product and stores the charges that have changed
        """

        # candidate for charge changes
        reactant_atoms = []
        product_atoms = []

        for molecule in self._reactant:
            reactant_atoms.extend(molecule.atomList)

        for molecule in self._product:
            product_atoms.extend(molecule.atomList)

        for atom in reactant_atoms:
            if 'CHG' in atom.attribs.keys():
                self._reactant_charges_changed.append(atom)

        for atom in product_atoms:
            if 'CHG' in atom.attribs.keys():
                self._product_charges_changed.append(atom)

    def store_bonds_order_changed(self):
        """
        Compares both Reactant and Product and stores the bonds which their bond order has changed during the reaction process.
        """

        # temp List of bonds
        reactant_bonds = []
        product_bonds = []
        product2_bonds = []

        # add all bonds to temporary bond list
        for molecule in self._reactant:
            reactant_bonds.extend(molecule.bondList)

        for molecule in self._product:
            product_bonds.extend(molecule.bondList)
            product2_bonds.extend(molecule.bondList)

        # set _product_bonds_order_change
        for reactant_bond in reactant_bonds:
            for product_bond in product_bonds:
                if reactant_bond.__eq__(product_bond):
                    product_bonds.remove(product_bond)

        for product_bond_appeared in self._product_bonds_appeared:
            for product_bond in product_bonds:
                if product_bond_appeared.__eq__(product_bond):
                    product_bonds.remove(product_bond)

        self._product_bonds_order_change = product_bonds

        #set _reactant_bonds_order_change
        for product_bond in product2_bonds:
            for reactant_bond in reactant_bonds:
                if product_bond.__eq__(reactant_bond):
                    reactant_bonds.remove(reactant_bond)

        for reactant_bond_appeared in self._reactant_bonds_appeared:
            for reactant_bond in reactant_bonds:
                if reactant_bond_appeared.__eq__(reactant_bond):
                    reactant_bonds.remove(reactant_bond)

        self._reactant_bonds_order_change = reactant_bonds

    def store_bonds_appeared_and_disapeared(self):
        """
        Compares both Reactant and Product and stores the bonds that have appeared and disappeared during the reaction process.

        """

        # temp List of bonds
        reactant_bonds = []
        product_bonds = []
        product2_bonds = []

        # add all bonds to temporary bond list
        for molecule in self._reactant:
            reactant_bonds.extend(molecule.bondList)

        for molecule in self._product:
            product_bonds.extend(molecule.bondList)
            product2_bonds.extend(molecule.bondList)

        # set _product_bonds_appeared and _reactant_bonds_disappeared
        for reactant_bond in reactant_bonds:
            for product_bond in product_bonds:
                if ((reactant_bond.fromAtom == product_bond.fromAtom and reactant_bond.toAtom == product_bond.toAtom) or (reactant_bond.fromAtom == product_bond.toAtom and reactant_bond.toAtom == product_bond.fromAtom)):
                    product_bonds.remove(product_bond)

        self._product_bonds_appeared = product_bonds
        self._reactant_bonds_disappeared = product_bonds

        #set _reactant_bonds_appeared and _product_bonds_disappeared
        for product_bond in product2_bonds:
            for reactant_bond in reactant_bonds:
                if ((product_bond.fromAtom == reactant_bond.fromAtom and product_bond.toAtom == reactant_bond.toAtom) or (product_bond.fromAtom == reactant_bond.toAtom and product_bond.toAtom == reactant_bond.fromAtom)):
                    reactant_bonds.remove(reactant_bond)

        self._reactant_bonds_appeared = reactant_bonds
        self._product_bonds_disappeared = reactant_bonds


    def generate_reactant_distractors(self):
        """
        Generates and returns Reactant Molecule distractors.

        """
        generated_distractors = []

        generated_distractors.extend(self.expand_molecule(self._reactant, self._reactant_bonds_order_change))
        generated_distractors.extend(self.expand_molecule(self._reactant, self._reactant_bonds_appeared))
        generated_distractors.extend(self.mutate_bond_order(self._reactant, self._reactant_bonds_order_change))
        generated_distractors = self.remove_molecules_generated_correctly(self._reactant, generated_distractors)

        return generated_distractors

    def generate_product_distractors(self):
        """
        Generates and returns Product Molecule distractors.

        """
        generated_distractors = []

        generated_distractors.extend(self.mutate_bond_order(self._product, self._product_bonds_order_change))
        generated_distractors.extend(self.mutate_bond_order(self._product, self._product_bonds_appeared))
        generated_distractors.extend(self.expand_molecule(self._product, self._product_bonds_order_change))
        generated_distractors.extend(self.expand_molecule(self._product, self._product_bonds_appeared))
        generated_distractors.extend(self.return_atoms_moved(self._product, self._product_bonds_disappeared, self._atoms_moved_to_product))

        generated_distractors = self.remove_molecules_generated_correctly(self._product, generated_distractors)

        return generated_distractors

    def expand_molecule(self, molecules, order_bonds_changed):
        """
        Expands a molecule by adding a Carbon.

        """
        # if charges change size is zero then pass this strategy
        results = []

        # get the max aam number Note: the length of the list does not give you the max aam number
        reaction_aam_count = 0
        for molecule in molecules:
            #print str(molecule.numberOfAtoms())
            for atom in molecule.atomList:
                if atom.aam > reaction_aam_count:
                    reaction_aam_count = atom.aam
        reaction_aam_count += 1

        for molecule in molecules:
            for bond in order_bonds_changed:
                if bond in molecule.bondList:

                    temp_molecule = copy.deepcopy(molecule)

                    temp_bond = None
                    for candidate_bond in temp_molecule.bondList:
                        if candidate_bond == bond:
                            temp_bond = candidate_bond

                    # Will be replacing the bond with something new,
                    # so let's break the molecule on the bond:
                    shifting_group = chem.get_subgraph_atoms(temp_molecule.bondList, temp_bond.toAtom, ignore_bonds=[temp_bond])
                    #atoms_2 = [a for a in molecule.atomList if a not in shifting_group]

                    # Shift vector for shifting_group
                    v = (temp_bond.toAtom.x - temp_bond.fromAtom.x, temp_bond.toAtom.y - temp_bond.fromAtom.y)
                    # Old location of toAtom becomes location of new atom
                    u = (temp_bond.toAtom.x, temp_bond.toAtom.y)

                    # Shift atoms that need shifting
                    for a in shifting_group:
                        a.x += v[0]
                        a.y += v[1]

                    # Place the new atom
                    atom = chem.Atom('C', u[0], u[1], 0, 0, reaction_aam_count, {}, reaction_aam_count)
                    orders = [1, bond.order]
                    random.shuffle(orders)
                    new_bond = chem.Bond(0, orders[0], atom, bond.toAtom)
                    previous_bond = chem.Bond(0, orders[1], bond.fromAtom, atom)

                    reaction_aam_count += 1

                    temp_molecule.bondList.remove(temp_bond)
                    temp_molecule.addAtom(atom)
                    temp_molecule.addBond(new_bond)
                    temp_molecule.addBond(previous_bond)

                    results.append(temp_molecule)

                    # I don't understand the following part. - VB

                    # if the bond is other then 2
                    # if bond.order == 2:
                    #     temp_molecule_second_option = copy.deepcopy(molecule)
                    #
                    #     atom = chem.Atom('C', 0, 0, 0, 0, reaction_aam_count, {}, reaction_aam_count)
                    #     new_bond = chem.Bond(0, bond.order, atom, bond.toAtom, {})
                    #     previous_bond = chem.Bond(0, 1, bond.fromAtom, atom, {})
                    #
                    #     temp_molecule_second_option.bondList.remove(bond)
                    #     temp_molecule_second_option.addAtom(atom)
                    #     temp_molecule_second_option.addBond(new_bond)
                    #     temp_molecule_second_option.addBond(previous_bond)
                    #
                    #     results.append(temp_molecule_second_option)
        return results

    def return_atoms_moved(self, molecules, bonds_disappeared, atoms_moved ):
        """
        Moves atoms back to their initial molecule
        """

        results = []

        # For ever atoms moved
        for atom_moved in atoms_moved:
            # Get the disappearing bonds
            for bond_disappeared in bonds_disappeared:

                if bond_disappeared.fromAtom.__eq__(atom_moved) and ATOM_VALENCE.get( bond_disappeared.toAtom.symbol ) != 1 and ATOM_VALENCE.get( bond_disappeared.fromAtom.symbol ) != 1:

                    molecules_copy = copy.deepcopy(molecules)
                    for molecule in molecules_copy:
                        if bond_disappeared.toAtom in molecule.atomList:

                            # we want to check if adding back this atom will cause any problems to the molecule
                            from_atom_bonds = self.get_atom_bonds(bond_disappeared.toAtom, copy.deepcopy(molecule))

                            #  if any of these bond have a order > 1 then reduce them
                            bonds_order_greater_then_one = []
                            for from_atom_bond in from_atom_bonds:
                                if from_atom_bond.order > 1:
                                    bonds_order_greater_then_one.append(from_atom_bond)

                            if bond_disappeared.order == 1 and bond_disappeared.toAtom.symbol != 'H' and bond_disappeared.fromAtom.symbol != 'H':

                                molecule_copy = copy.deepcopy(molecule)
                                if len(bonds_order_greater_then_one) > 0 and bonds_order_greater_then_one[0] in molecule_copy.bondList:

                                    molecule_copy.bondList.remove(bonds_order_greater_then_one[0])
                                    bonds_order_greater_then_one[0].order = 1
                                    molecule_copy.bindList.append(bonds_order_greater_then_one[0])
                                    atom_copy = copy.deepcopy(atom_moved)
                                    bond_copy = copy.deepcopy(bond_disappeared)
                                    bond_copy.fromAtom = atom_copy
                                    bond_copy.order = 2
                                    bond_copy.toAtom = molecule_copy.get_atom_by_aam(bond_copy.toAtom.aam)
                                    molecule_copy.addBond(bond_copy)
                                    molecule_copy.addAtom(atom_moved)
                                    molecule_copy.assign_xyz(atom_copy)

                                    results.append(molecule_copy)

                            molecule_copy = copy.deepcopy(molecule)
                            atom_copy = copy.deepcopy(atom_moved)
                            bond_copy = copy.deepcopy(bond_disappeared)
                            bond_copy.fromAtom = atom_copy
                            bond_copy.toAtom = molecule_copy.get_atom_by_aam(bond_copy.toAtom.aam)
                            molecule_copy.addBond(bond_copy)
                            molecule_copy.addAtom(atom_moved)
                            molecule_copy.assign_xyz(atom_copy)

                            results.append(molecule_copy)

                elif bond_disappeared.toAtom.__eq__(atom_moved) and ATOM_VALENCE.get( bond_disappeared.toAtom.symbol ) != 1 and ATOM_VALENCE.get( bond_disappeared.fromAtom.symbol ) != 1:

                    molecules_copy = copy.deepcopy(molecules)
                    for molecule in molecules_copy:
                        if bond_disappeared.fromAtom in molecule.atomList:

                            # we want to check if adding back this atom will cause any problems to the molecule
                            to_atom_bonds = self.get_atom_bonds(bond_disappeared.fromAtom, copy.deepcopy(molecule))

                            bonds_order_greater_then_one = []
                            for to_atom_bond in to_atom_bonds:
                                if to_atom_bond.order > 1:
                                    bonds_order_greater_then_one.append(to_atom_bond)

                            if bond_disappeared.order == 1 and bond_disappeared.toAtom.symbol != 'H' and bond_disappeared.fromAtom.symbol != 'H':

                                molecule_copy = copy.deepcopy(molecule)
                                if len(bonds_order_greater_then_one) > 0 and bonds_order_greater_then_one[0] in molecule_copy.bondList:

                                    molecule_copy.bondList.remove(bonds_order_greater_then_one[0])
                                    bonds_order_greater_then_one[0].order = 1
                                    molecule_copy.bondList.append(bonds_order_greater_then_one[0])
                                    atom_copy = copy.deepcopy(atom_moved)
                                    bond_copy = copy.deepcopy(bond_disappeared)
                                    bond_copy.toAtom = atom_copy
                                    bond_copy.order = 2
                                    bond_copy.fromAtom = molecule_copy.get_atom_by_aam(bond_copy.fromAtom.aam)
                                    molecule_copy.addBond(bond_copy)
                                    molecule_copy.addAtom(atom_copy)
                                    molecule_copy.assign_xyz(atom_copy)

                                    results.append(molecule_copy)

                            molecule_copy = copy.deepcopy(molecule)
                            atom_copy = copy.deepcopy(atom_moved)
                            bond_copy = copy.deepcopy(bond_disappeared)
                            bond_copy.toAtom = atom_copy
                            bond_copy.fromAtom = molecule_copy.get_atom_by_aam(bond_copy.fromAtom.aam)
                            molecule_copy.addBond(bond_copy)
                            molecule_copy.addAtom(atom_copy)
                            molecule_copy.assign_xyz(atom_copy)

                            results.append(molecule_copy)
        return results

    # 1. if there is a charge in one of the Atoms remove it or flip it
    # This Condition doesn't require any graph structure to be acomplished. All is required is the molcule
    def mutate_charges(self, molecules, charges_changed ):

        results = []
        for molecule in molecules:
            # we get the product charges
            for atom_charge in charges_changed:
                # and for every charged atom check if it's in the particular molecule
                for atom in molecule.atomList:
                    if atom_charge.__eq__(atom):
                        # if atom has a negative change it to pos or remove
                        if atom_charge.attribs['CHG'] == '-1':
                            # choose Randomly if charge will be flipped or deleted
                            if bool(random.getrandbits(1)):
                                atom.attribs['CHG'] = '1'
                                results.append(copy.deepcopy(molecule))
                                # return attribute to it's original state
                                atom.attribs['CHG'] = '-1'
                            else:
                                del atom.attribs['CHG']
                                results.append(copy.deepcopy(molecule))
                                # return attribute to it's original state
                                atom.attribs.update({'CHG': '-1'})
                        # atom has a positive charge flip it or remove
                        elif atom_charge.attribs['CHG'] == '1':
                            if bool(random.getrandbits(1)):
                                atom.attribs['CHG'] = '-1'
                                results.append(copy.deepcopy(molecule))
                                # return attribute to it's original state
                                atom.attribs['CHG'] = '1'
                            else:
                                del atom.attribs['CHG']
                                results.append(copy.deepcopy(molecule))
                                # return attribute to it's original state
                                atom.attribs.update({'CHG' : '1' })
        return results


    def remove_molecules_generated_correctly(self, molecules, results):
        """
         Remove any molecules that have been generated correctly
        """

        for molecule in molecules:
            for result in results:
                if molecule.__eq__(result):
                    results.remove(result)

        return results


    def get_atom_bonds(self, atom, molecule):
        """
        Returns atom bonds
        """
        bonds = []

        for bond in molecule.bondList:
            if bond.toAtom.__eq__(atom):
                bonds.append(bond)
            elif bond.fromAtom.__eq__(atom):
                bonds.append(bond)

        return bonds



    def mutate_bond_order(self, molecules, candidate_bonds):
        """
        Mutates candidate Bonds orders
        """
        results = []

        for molecule in molecules:
            for candidate_bond in candidate_bonds:
                    for bond in molecule.bondList:
                            # TODO this will need to be improved
                            if  candidate_bond.__eq__(bond) and ATOM_VALENCE.get( bond.toAtom.symbol ) != 1 and ATOM_VALENCE.get( bond.fromAtom.symbol ) != 1:
                                if bond.order == 2:
                                    bond.order -= 1
                                    results.append(copy.deepcopy(molecule))
                                    bond.order += 1
                                elif bond.order == 1:
                                    bond.order += 1
                                    results.append(copy.deepcopy(molecule))
                                    bond.order -= 1
                                elif bond.order == 3:
                                    bond.order = 1
                                    results.append(copy.deepcopy(molecule))
                                    bond.order = 2
                                    results.append(copy.deepcopy(molecule))
                                    bond.order = 3

        return results
