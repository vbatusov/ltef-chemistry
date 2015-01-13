"""
Let us maintain a single catalog instance for the entire server;
Let the catalog contain a dictionary { "reaction_basename" : generic_reaction_object }
This way, we parse each reaction file once on startup. Parsing is based on paths and names 
given in YAML file; reaction objects are assigned their full names and descriptions (from .txt)
as attributes.


RULE CHANGE:
This will now house DB-related startup tasks:
 - As before, load reactions from files;
 - Check reactions against DB - by basename for existence, by timestamp for decrepitude;
 - Update DB as necessary or complain if can't;
Invariant: pairs (id,basename) must be preserved
TODO: switch views.py to use DB instead of objects?
"""

import yaml
import os
import datetime
import sys
sys.path.append('../python')
import rxn
import chem

import transaction
from .models import (
    DBSession,
    Group,
    User,
    Reac,
    List,
    )

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

        # And this to store everything plus file info
        disk_data = []

        # This will map basenames to full names
        self.base_to_full = {}

        # Read YAML file
        yaml_obj = self._get_yaml_object()
        path_to_rxn = yaml_obj["rxn_dir"]
        path_to_desc = yaml_obj["descriptions_dir"]
        desc_mtime = os.path.getmtime(path_to_desc)
        reaction_names = yaml_obj["reactions"]

        # Read and parse all RXN
        for entry in reaction_names:
            basename = entry["basename"]
            path = os.path.join(path_to_rxn, basename + ".rxn")
            rxn_mtime = os.path.getmtime(path)

            # Whichever is the latest
            mtime = max(desc_mtime, rxn_mtime)

            reaction = rxn.parse_rxn(path)
            reaction.full_name = entry["name"]
            reaction.desc = self._get_reaction_description(path_to_desc, basename)

            self._reactions[basename] = reaction
            self.base_to_full[basename] = entry["name"]

            disk_data.append((basename, path, datetime.datetime.fromtimestamp(mtime), reaction.full_name, reaction.desc, reaction))

        self._update_DB(disk_data)


    def _update_DB(self, disk_data):
        print "Synchronizing DB with files..."
        reacs = DBSession.query(Reac).all()

        print "%d reaction files on disk." % len(disk_data)
        print "%d reactions recorded in the database." % len(reacs)

        # Disk to DB sync
        print "Updating DB with new data..."
        for (b, s, st, fn, d, o) in disk_data:
            # Since Reac.basename is unique, there can only be one result, if any
            db_reac = DBSession.query(Reac).filter(Reac.basename == b).first()
            # No DB entry for this basename => create entry
            if db_reac is None:
                #with transaction.manager:
                DBSession.add(Reac(basename=b, source=s, source_timestamp=st, full_name=fn, description=d))
                print "Added new reaction '" + b + "' to database due to previously unknown basename."
            # DB entry is old according to timestamps => update
            elif db_reac.source_timestamp < st:
                #with transaction.manager:
                DBSession.query(Reac).filter(Reac.basename == b)\
                    .update({"source" : s, "source_timestamp" : st, "full_name" : fn, "description" : d})
                print "Updated reaction '" + b + "' in database due to file (rxn or description) timestamp."

        # DB to disk sync
        print "Removing old data from DB..."
        delquery = DBSession.query(Reac)
        for (b, s, st, fn, d, o) in disk_data:
            delquery = delquery.filter(Reac.basename != b)

        if len(delquery.all()) > 0:
            print "Removing " + str(len(delquery.all())) + " outdated reaction records from DB..."
            #with transaction.manager:
            delquery.delete()

        # Repopulate the list of all reactions in the lists table
        # [1,6,5] - a list of reaction id's; order is significant
        # Drop the old list
        DBSession.query(List).filter(List.title == List.ALL_TITLE).delete()
        # Get a list of all reaction id's out of DB
        list_all = [reac.id for reac in DBSession.query(Reac).all()]
        # Get the admin's id
        admin_id = DBSession.query(User).filter(User.username=="admin").first().id
        # Add the new list back        
        DBSession.add(List(owner=admin_id, title=List.ALL_TITLE, desc=List.ALL_DESC, data=list_all))

        transaction.commit()        

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


    def get_selectbox_lists_by_list_id(self, list_id):
        """
            Lists of tuples (full reaction name, reaction id);
            left: those in list_id
            right: those in List.ALL_TITLE but not in list_id
        """
        left = []
        right = []

        all_reacs_list_id = DBSession.query(List).filter(List.title == List.ALL_TITLE).first().id

        list_of_all_ids = DBSession.query(List).filter(List.id == all_reacs_list_id).first().data
        list_of_right_ids = DBSession.query(List).filter(List.id == list_id).first().data
        
        print "+++++++++++++++++++++++++++++++++++"
        print "List of all   ids: " + str(list_of_all_ids)
        print "List of right ids: " + str(list_of_right_ids)

        all_reacs = DBSession.query(Reac).filter(Reac.id.in_(list_of_all_ids)).order_by(Reac.full_name).all()

        for reac in all_reacs:
            if reac.id in list_of_right_ids:
                right.append((reac.full_name, reac.id))
            else:
                left.append((reac.full_name, reac.id))

        print str((left, right))

        return (left, right)


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



