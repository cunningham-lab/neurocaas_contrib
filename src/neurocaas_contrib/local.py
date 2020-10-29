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

## 8/20.20 Sketch out a new class that will form the basis of the new python package.  
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
        TODO


    def initialize_blueprint(instance_type,ami,region):
        """
        Initializes a blueprint with the basic info needed to get an instance up and running.    
        ## Creates a special directory where pipeline specific information will be stored.  
        """

    def load_blueprint(path):
        """
        If continuing development on a pipeline that already exists, you can load the information from it directly. 
        """

    def launch_development_instance():
        """
        Launch a development instance from the blueprint you are building. 
        """



