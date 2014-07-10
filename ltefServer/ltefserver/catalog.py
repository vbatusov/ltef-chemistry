"""
Let us maintain a single catalog instance for the entire server;
Let the catalog contain a dictionary { "reaction_basename" : generic_reaction_object }
This way, we parse each reaction file once on startup. Parsing is based on paths and names 
given in YAML file; reaction objects are assigned their full names and descriptions (from .txt)
as attributes.
"""

import yaml
import os
import sys
sys.path.append('../python')
import rxn
import chem

YAML_PATH = "reactions/catalogue.yml"

class Catalog:
    """ This class will have a single instance for the entire web application;
    It will maintain a dictionary mapping reaction basenames to generic reaction objects;
    Threads will access the reaction dictionary in a thread-safe manner.
    """

    def __init__(self):
        """ Read and parse all reactions.
        """

        # This will store everything
        self._reactions = {}

        # This will map basenames to full names
        self.base_to_full = {}

        # Read YAML file
        yaml_obj = self._get_yaml_object()
        path_to_rxn = yaml_obj["rxn_dir"]
        path_to_desc = yaml_obj["descriptions_dir"]
        reaction_names = yaml_obj["reactions"]

        # Read and parse all RXN
        for entry in reaction_names:
            basename = entry["basename"]
            path = os.path.join(path_to_rxn, basename + ".rxn")

            reaction = rxn.parse_rxn(path)
            reaction.full_name = entry["name"]
            reaction.desc = self._get_reaction_description(path_to_desc, basename)

            self._reactions[basename] = reaction
            self.base_to_full[basename] = entry["name"]

        # DEBUG
        print "Catalog init finished with: "
        for bn in self.get_sorted_basenames():
            print "  " + bn + " : " + str(id(self._reactions[bn]))


    def _get_yaml_object(self):
        global YAML_PATH
        
        f_config = open(YAML_PATH, 'r')
        yml_data = f_config.read()
        f_config.close()
        yaml_obj = yaml.load(yml_data)

        return yaml_obj


    def _get_reaction_description(self, path_to_desc, basename):
        filepath = os.path.join(path_to_desc, basename + '.txt')
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

    def get_sorted_basenames(self):
        return sorted(self._reactions.keys())

    def get_reaction_by_basename(self, basename):
        return self._reactions[basename]


    # def get_reactions_info_from_files(folder):
    #     dataList = []
    #     for filename in os.listdir(folder):
    #         file_path = os.path.join(folder, filename)
    #         data = {}
    #         data["basename"] = os.path.splitext(os.path.basename(filename))[0]
    #         data["name"] = data["basename"]
    #         #print "Filename: " + str(filename)
    #         #print "Location: " + str(file_path)
    #         #print ""
    #         dataList.append(data)
    #     everything = {}
    #     everything["rxn_dir"] = "/home/vitaliy/ltef_project/ltef-chemistry/reactions/corrected_chris/rxn_test/"
    #     everything["descriptions_dir"] = "/home/vitaliy/ltef_project/ltef-chemistry/reactions/corrected_chris/descriptions/"
    #     everything["reactions"] = dataList
    #     print yaml.dump(everything)

    #get_reactions_info_from_files("/home/vitaliy/ltef_project/ltef-chemistry/reactions/corrected_chris/rxn_test/")


    # def get_path_to_rxn():
    #     obj = _get_yaml_object()
    #     return obj["rxn_dir"]

    # def get_path_to_desc():
    #     obj = _get_yaml_object()
    #     return obj["descriptions_dir"]

    # def get_reaction_names():
    #     obj = _get_yaml_object()
    #     return obj["reactions"]

    # def get_reaction_names_sorted():
    #     return sorted(get_reaction_names(), key=lambda k: k['basename']) 

    # def get_reaction_dict():
    #     """ basename -> full name
    #     """
    #     dictionary = {}    
    #     for entry in get_reaction_names_sorted():
    #         dictionary[entry["basename"]] = entry["name"]
    #     return dictionary



