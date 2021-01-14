## Module to manage blueprint creation and updating. 
import docker
from collections import deque
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
    def write(self):
        """Write back to the original source file:

        """
        with open(self.config_filepath,"w") as f:
            json.dump(self.blueprint_dict,f,indent = 4)

    def update_container_history(self,container_name):        
        """Updates the container history with a most recent entry. #TODO check that this container exists.

        :param container_name: name of the container.
        """
        container_history = deque(self.blueprint_dict.get("container_history",[]),maxlen = 5)
        container_history.append(container_name)
        self.blueprint_dict["container_history"] = list(container_history)
    
    @property
    def active_container(self):
        """First check if container is running

        """
        return self.blueprint_dict.get("container_history",[None])[-1]

    @property
    def active_container_status(self):
        """First check if container is running

        """
        containername = self.blueprint_dict.get("container_history",[None])[-1]
        if containername is None:
            return containername
        try:
            client = docker.from_env()
            cont = client.containers.get(containername)
            status = cont.status
            containernamestatus = f"{containername} ({status})"
        except docker.errors.NotFound:    
            containernamestatus = containername 
        return containernamestatus 

    def update_image_history(self,image_name):    
        """Updates the image history with a most recent entry. #TODO check that this image exists.

        :param image_name: name of the image to update with. 
        """
        image_history = deque(self.blueprint_dict.get("image_history",[]),maxlen = 5)
        image_history.append(image_name)
        self.blueprint_dict["image_history"] = list(image_history)

    @property
    def active_image(self):
        return self.blueprint_dict.get("image_history",[None])[-1]
        #return self._active_image
    #@active_image.getter
    #def active_image(self):
    #    self._active_image = self.blueprint_dict.get("image_history",[None])[-1]
