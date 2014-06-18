ltef.py
=======

is the command-line interface to everything.

Usage
----
Overall:
```
[vitaliy@localhost python]$ python ltef.py --help
usage: ltef.py [-h] {pddl,draw} ... rxn_file output_dir

Reads an RXN v3000 file; depening on parameters, either renders the reaction
using Indigo into png, or generates PDDL for the reaction.

positional arguments:
  {pddl,draw}
    pddl       Selects PDDL generation mode.
    draw       Selects .png drawing mode.
  rxn_file     The RXN v3000 file.
  output_dir   Output directory.

optional arguments:
  -h, --help   show this help message and exit
```

For pddl:
```
$ python ltef.py pddl --help
usage: ltef.py pddl [-h] [--all] [--domain] [--instance]

optional arguments:
  -h, --help  show this help message and exit
  --all       Equivalent to "--domain --instance"
  --domain    Generate the PDDL domain description for reaction
  --instance  Generate a randomized PDDL instance of the reaction
```

Example. The following command generates whatever PDDL it can from the RXN file "alkyne_hydrogenation_with_lindlar\'s_catalyst.rxn" located in the directory "../reactions/corrected_chris/rxn_test" and puts the result in the directory "pddl_dir"
```sh
python ltef.py pddl --all ../reactions/corrected_chris/rxn_test/alkyne_hydrogenation_with_lindlar\'s_catalyst.rxn pddl_dir
```

What else?
----

* chem.py: defines the classes Atom, Molecule, Reaction; provides basic chemical manipulations (instantiates generic molecules, generates arbitrary alkyls, etc.)
* pddl.py: all PDDL-related code
* rxn.py: RXN parser; reads RXNv3000, produces chem objects
* rxn.fsm: RXN parser config

