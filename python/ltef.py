import argparse
import rxn
import pddl
import draw
import os.path
import sys
import chem


def gen_pddl(args, reaction):

    if args.domain or args.all:
        print "Generating PDDL domain description...\n"
                
        print "\nThis is what I was able to get out of the RXN:"
        print str(reaction)

        pddl_domain = pddl.getDomain(reaction)

        print pddl_domain

        domain_file = os.path.join(args.output_dir,  "domain_" + reaction.name + ".pddl")
        out = open(domain_file, 'w')
        out.write(pddl_domain + "\n")
        out.close()
        print "\nPDDL domain description written to " + domain_file

        # Insert an empty line for clarity
        if args.all:
            print ""

    if args.instance or args.all:
        print "Generating a randomized PDDL instance..."
        print "(Instance generation not implemented yet.)"

        #instance = reaction.getInstance()

        #pddl_domain = pddl.getDomain(instance)

        #print pddl_domain


def gen_img(args, reaction):
    print "Generating pictures."

    pic = draw.renderReactionToBuffer(reaction)

    #print "Bytes:"
    #print str(pic)
    img_file = os.path.join(args.output_dir,  "reaction_" + reaction.name + ".png")
    out = open(img_file, 'wb')
    out.write(pic)
    out.close()
    print "\nReaction picture written to " + img_file
    


# Create the argparser
# https://docs.python.org/dev/library/argparse.html

parser = argparse.ArgumentParser(description='Reads an RXN v3000 file; depening on parameters, either renders the reaction using Indigo into png, or generates PDDL for the reaction.')

subparsers = parser.add_subparsers()

parser_pddl = subparsers.add_parser('pddl', help="Selects PDDL generation mode.")
parser_pddl.add_argument('--all', action='store_const', const=True, default=False, help='Equivalent to "--domain --instance "')
parser_pddl.add_argument('--domain', action='store_const', const=True, default=False, help='Generate the PDDL domain description for reaction')
parser_pddl.add_argument('--instance', action='store_const', const=True, default=False, help='Generate a randomized PDDL instance of the reaction')
parser_pddl.set_defaults(func=gen_pddl)

parser_draw = subparsers.add_parser('draw', help="Selects .png drawing mode.")
parser_draw.add_argument('--all', action='store_const', const=1, default=0, dest='what', help='Output all images (currently the only option, so it\'s redundant).')
parser_draw.set_defaults(func=gen_img)

parser.add_argument('rxn_file',  type=str, help='The RXN v3000 file.')
parser.add_argument('output_dir', type=str, default='.', help='Output directory.')

args = parser.parse_args()


# Debug
#print args

if args.func == gen_pddl and not (args.all or args.domain or args.instance):
    parser_pddl.error('No action requested, add any of: {--all, --domain, --instance}')

# Check if rxn file and output folder exist
if not os.path.isfile(args.rxn_file):
    raise IOError("Cannot open file " + args.rxn_file)

if not os.path.isdir(args.output_dir):
    raise IOError("Cannot open directory " + args.rxn_file)

# Parse the RXN file, get a generic reaction
reaction = rxn.parse_rxn(args.rxn_file)

args.func(args, reaction)