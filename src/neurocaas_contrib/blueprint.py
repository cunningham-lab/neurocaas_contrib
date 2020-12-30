## Module to manage blueprint creation and updating. 
import json

class Blueprint(object):
    """Blueprint object to manage blueprint entry read/write.  

    Inputs:
    :param path: Path to a blueprint object. 

    """
    def __init__(self,path):
        """Constructor. 

        """
        self.config_filepath = path
        with open(self.config_filepath,"r") as f:
            config = json.load(f)
        self.blueprint_dict = config

    def reload(self):
        """Reload the blueprint from file. 

        """
        with open(self.config_filepath,"r") as f:
            self.blueprint_dict = config
