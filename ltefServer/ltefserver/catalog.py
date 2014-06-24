"""
Read YAML, return a list of known reactions;
Read YAML, return paths to RXN and descriptions
"""

import yaml
import os
import sys
sys.path.append('../python')
import rxn
import chem

YAML_PATH = "reactions/catalogue.yml"
YAML_OBJ = None

def get_reactions_info_from_files(folder):
    dataList = []
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        data = {}
        data["basename"] = os.path.splitext(os.path.basename(filename))[0]
        data["name"] = data["basename"]
        #print "Filename: " + str(filename)
        #print "Location: " + str(file_path)
        #print ""
        dataList.append(data)
    everything = {}
    everything["rxn_dir"] = "/home/vitaliy/ltef_project/ltef-chemistry/reactions/corrected_chris/rxn_test/"
    everything["descriptions_dir"] = "/home/vitaliy/ltef_project/ltef-chemistry/reactions/corrected_chris/descriptions/"
    everything["reactions"] = dataList
    print yaml.dump(everything)

#get_reactions_info_from_files("/home/vitaliy/ltef_project/ltef-chemistry/reactions/corrected_chris/rxn_test/")


def get_path_to_rxn():
    obj = get_yaml_object()
    return obj["rxn_dir"]

def get_path_to_desc():
    obj = get_yaml_object()
    return obj["descriptions_dir"]

def get_reaction_names():
    obj = get_yaml_object()
    return obj["reactions"]

def get_reaction_names_sorted():
    return sorted(get_reaction_names(), key=lambda k: k['basename']) 

def get_reaction_dict():
    """ basename -> full name
    """
    dictionary = {}    
    for entry in get_reaction_names_sorted():
        dictionary[entry["basename"]] = entry["name"]
    return dictionary

def get_reaction_description(basename):
    filepath = os.path.join(get_path_to_desc(), basename + '.txt')
    desc = "(No description available)"

    try:
        if os.path.isfile(filepath):
            f = open(filepath, 'r')
            desc = f.read()
            f.close()
        else:
            f = open(filepath, 'w')
            f.write(desc + "\n")
            f.close()
            
    except Exception, e:
        print e

    return desc

def get_yaml_object():
    global YAML_PATH
    global YAML_OBJ
    if YAML_OBJ is None:
        f_config = open(YAML_PATH, 'r')
        yml_data = f_config.read()
        f_config.close()
        YAML_OBJ = yaml.load(yml_data)

    return YAML_OBJ
