import argparse
import rxn
import pddl
import os.path
import sys
import chem


def gen_pddl(args):
    print "Generating PDDL code for EVERYTHING."
    reaction = rxn.parse_rxn(args.rxn_file)
    instance = reaction.getInstance()
    print str(reaction)
    pddl_domain = pddl.getDomain(reaction)

    # THen, generate problem instances
    



def gen_img(args):
    print "Generating pictures of EVERYTHING."
    print "Sorry, this feature is not implemented yet."


# Create the argparser
# https://docs.python.org/dev/library/argparse.html

parser = argparse.ArgumentParser(description='Reads an RXN v3000 file; depening on parameters, either renders the reaction using Indigo into png, or generates PDDL for the reaction.')

subparsers = parser.add_subparsers()

parser_pddl = subparsers.add_parser('pddl', help="Selects PDDL generation mode.")
parser_pddl.add_argument('--all', action='store_const', const=1, default=0, dest='what', help='Output all PDDL (currently the only option, so it\'s redundant).')
parser_pddl.set_defaults(func=gen_pddl)

parser_draw = subparsers.add_parser('draw', help="Selects .png drawing mode.")
parser_draw.add_argument('--all', action='store_const', const=1, default=0, dest='what', help='Output all images (currently the only option, so it\'s redundant).')
parser_draw.set_defaults(func=gen_img)

parser.add_argument('rxn_file',  type=str, help='The RXN v3000 file.')
parser.add_argument('output_dir', type=str, default='.', help='Output directory.')

args = parser.parse_args()

# Debug
print args

# Check if rxn file and output folder exist
if not os.path.isfile(args.rxn_file):
    raise IOError("Cannot open file " + args.rxn_file)

if not os.path.isdir(args.output_dir):
    raise IOError("Cannot open directory " + args.rxn_file)

args.func(args)