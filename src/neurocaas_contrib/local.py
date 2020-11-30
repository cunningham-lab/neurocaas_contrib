## A module to work with AMIs for the purpose of debugging and updating.
import boto3
import sys
import time
import os
import re
import datetime
import subprocess
import json
import pathlib

cfn_client = boto3.client("cloudformation")

## 11/23/20
class NeuroCAASAutoScript(object):
    """Developer tool to automate creation and testing of an analysis-specific bash script.   

    """
    def __init__(self,scriptjson,templatepath):
        """
        :param scriptjson: a json script that specifies all of the parameters necessary to set up a local analysis environment. Tells us to start a python environment check if we need to communicate to the gpu, as well as the locations to which we should load local data and write output. 
        """
        ## Check for all necessary arguments in the config file:
        with open(scriptjson,"r") as f:
            scriptdict = json.load(f)
        args_req = {"script_name":str,"in":dict,"out":dict,"user_root_dir":str}
        for ar in args_req: 
            assert ar in scriptdict.keys()
            assert type(scriptdict[ar]) == args_req[ar], "scriptdict is misformatted: type for '{}' is {}, should be {}".format(ar,type(ar),args_req[ar])
        self.scriptdict = scriptdict

        ## Load in data from template script:
        with open(templatepath,"r") as f:
            scriptlines = (f.readlines())
        assert scriptlines[0].startswith("#!/bin/bash"), "We must initialize from and build a bash script."
        self.scriptlines = scriptlines

        ## Now we start doing setup: 
        if "dlami" in scriptdict.keys() is scriptdict["dlami"] is "true":
            self.add_dlami()

        if "env_name" in scriptdict.keys() and scriptdict["env_name"] is not None:
            if "conda_dir" in scriptdict.keys() and scriptdict["conda_dir"] is not None:
                path = scriptdict["conda_dir"]
                print(path,"conda_dir from path")
            else:
                path = None
                print("path is none")
            self.add_conda_env(path)

    def add_dlami(self):
        """Sources the dlami bash script to correctly configure the ec2 os environment with GPU. 

        """
        self.scriptlines.append("\n")
        self.scriptlines.append("## AUTO ADDED DLAMI SETUP \n")
        self.scriptlines.append("source .dlamirc")

    def append_conda_path_command(self,path = None):
        """Generates the material we want to append to the python path to find the anaconda environment correctly. Will assume that anaconda(3) is installed in the user's home directory. An alternative path to anaconda3/bin can be supplied if this is not the case.   
        :param path: (optional) if given, will check that the anaconda bin exists at that location, instead of being installed in the user's root directory
        :return: the bash command we will use to appropriately format the anaconda path. 
        """
        if path is None:
            path = os.path.join(self.scriptdict["user_root_dir"],"anaconda3/bin")
            
        ## First check that this path exists and is appropriately formatted.
        assert path.endswith("/bin"), "Path must end with *conda{}/bin."
        assert os.path.isdir(path),f"The path {path} does not exist. Please add/revise a manually added path to the anaconda bin."
        
        command = "export PATH=\"{}:$PATH\"".format(path)
        return command

    def check_conda_env(self,env_name):
        """Checks if a conda env exists on this machine, and returns a boolean exists/not exists.

        :param env_name: environment name. 
        :return: boolean, if this environment exists or not. 
        """

        all_env_str = subprocess.check_output('conda env list',shell = True).decode("utf-8")
        all_env_info = all_env_str.split("\n")[2:]
        condition = any([env_info.startswith(env_name+" ") for env_info in all_env_info])

        return condition 


    def add_conda_env(self,check = True,path = None):
        """Adds commands to enter a conda virtual environment to template script. If check, will check that this virtual environment exists before adding.  

        :param check: boolean asking if we should check that the environment exists first or not.
        :param path: (optional) if provided, looks here for the conda installation. Otherwise will defaults to $user_root_dir/conda_dir(anaconda3 if not provided).

        """
        env_name = self.scriptdict["env_name"]
        if check:
            assert self.check_conda_env(env_name),"conda environment must exist"

        setupcommand = self.append_conda_path_command(path)+" \n"
        declarecommand = f"conda activate {env_name}"+" \n"

        #Now add the suggested lines to the script:  
        self.scriptlines.append("\n")
        self.scriptlines.append("## AUTO ADDED ENV SETUP \n")
        self.scriptlines.append(setupcommand)
        self.scriptlines.append(declarecommand)



    def write_new_script(self,filename):
        """Writes the current contents of scriptlines to file. 

        :param filename: name of file to write to. 
        
        """
        with open(filename,"w") as f:
            f.writelines(self.scriptlines)

    def check_args():
        """

        """


## 8/20/20 Sketch out a new class that will form the basis of the new python package.  
class NeuroCAASDeveloperInterface(object):
    """New developer interface that will form the basis for a python package. 

    """
    def __init__(self,pipelinename):
        """
        ## 1. Checks that pipeline name is not already taken on account. Notifies if the name already exists (we can check this on pull request). 
        ## 2. Creates a tag value for the developer's IAM credentials that indicates they are working with pipeline of given name. Ensures that you can only work with one pipeline at a time, and that they are monitored. This tag value should be encrypted, so that developers cannot provide the tag manually and launch as many instances as they would like.  
        """
        try:
            response = cfn_client.describe_stacks(pipelinename)
        #TODO
        except:
            pass


    def initialize_blueprint(instance_type,ami,region):
        """
        Initializes a blueprint with the basic info needed to get an instance up and running.    
        ## Creates a special directory where pipeline specific information will be stored.  
        """
        pass

    def load_blueprint(path):
        """
        If continuing development on a pipeline that already exists, you can load the information from it directly. 
        """
        pass

    def launch_development_instance():
        """
        Launch a development instance from the blueprint you are building. 
        """
        pass

