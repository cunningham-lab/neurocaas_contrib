import pytest
from neurocaas_contrib.blueprint import Blueprint
import json
import os

thisdir = os.path.dirname(os.path.realpath(__file__))
fixtureblueprint = os.path.join(thisdir,"test_mats","stack_config_template.json")

class Test_Blueprint():
    def test_Blueprint(self):
        blueprint = Blueprint(fixtureblueprint)

    def test_Blueprint_update_container_history(self):
        blueprint = Blueprint(fixtureblueprint)
        containers = ["c{}".format(i) for i in range(7)]
        for c in containers:
            blueprint.update_container_history(c)
        assert json.dumps(blueprint.blueprint_dict)
        assert blueprint.blueprint_dict["container_history"] == containers[2:] 

    def test_Blueprint_update_image_history(self):
        blueprint = Blueprint(fixtureblueprint)
        images = ["i{}".format(i) for i in range(7)]
        for i in images:
            blueprint.update_image_history(i)
        assert json.dumps(blueprint.blueprint_dict)
        assert blueprint.blueprint_dict["image_history"] == images[2:] 
   
    def test_Blueprint_active_container(self):
       blueprint = Blueprint(fixtureblueprint)
       assert blueprint.active_container is None    
       containers = ["c{}".format(i) for i in range(7)]
       for c in containers:
           blueprint.update_container_history(c)
       assert blueprint.active_container == containers[-1]    

    def test_Blueprint_active_image(self):
       blueprint = Blueprint(fixtureblueprint)
       assert blueprint.active_image is None    
       images = ["i{}".format(i) for i in range(7)]
       for i in images:
           blueprint.update_image_history(i)
       assert blueprint.active_image == images[-1]    
       print(json.dumps(blueprint.blueprint_dict,indent = 4))

    def test_Blueprint_update_develop_history(self):    
        blueprint = Blueprint(fixtureblueprint)

