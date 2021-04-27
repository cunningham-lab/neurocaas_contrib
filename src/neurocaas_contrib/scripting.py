## module for scripting tools. 
import os
import io
import time
import datetime
import subprocess
import sys
import yaml
import json
import zipfile
from .log import NeuroCAASCertificate,NeuroCAASDataStatus

dir_loc = os.path.abspath(os.path.dirname(__file__))

if "pytest" in sys.modules:
    mode = "test"
else:
    mode = "std"

if mode == "test":
    configname = ".neurocaas_contrib_dataconfig.json"
    configpath = os.path.join(".",configname)

else:    
    configname = ".neurocaas_contrib_dataconfig.json"
    configpath = os.path.join(os.path.expanduser("~"),configname)

def get_yaml_field(yamlfile,fieldname):
    """returns the value of a field in a yaml file. 

    :param yamlfile: path to the yaml file you want to parse. 
    :param fieldname: the name of the field you want to extract. 
    """
    with open(yamlfile,"r") as f:
        ydict = yaml.full_load(f)
    try:    
        output = ydict[fieldname]
    except KeyError:    
        raise KeyError("No field {} exists in this yaml file.".format(fieldname))
    ftype = type(output)
    if ftype is not dict:
        return str(output)
    else:
        return json.dumps(output)

def parse_zipfile(zipname,path = None): 
    """Given a zipfile, confirms that it is a zipfile, and that it contains one top level directory. Unzips the zip file, and returns the name of the top level directory. Will throw an error if 1) the file path is not a zip file, or 2) if it contains more than one top level directory. 

    """
    assert zipfile.is_zipfile(zipname), "File is not a recognized zip archive"
    archive = zipfile.ZipFile(zipname)
    full_namelist = archive.namelist()
    folder = {item.split("/")[0] for item in full_namelist}.difference({'__MACOSX'})
    filtered_namelist = [fn for fn in full_namelist if not fn.startswith('__MACOSX')]
    assert len(folder) == 1; "Folder must contain only one top level directory." 
    if path is None:
        path = os.path.dirname(zipname)
    archive.extractall(path = path,members = filtered_namelist)
    return folder.pop()

## from https://stackoverflow.com/questions/18421757/live-output-from-subprocess-command
def log_process(command,logpath,s3status):
    """Given a path to an executable, runs it, logs output and prints to stdout. 

    :param processpath: command you want to run. 
    :param logpath: path where you will log the stdout/err outputs locally. 
    :param s3status: s3 path where the dataset is stored  
    :return: return code of the command. 
    """
    ncds = NeuroCAASDataStatusLegacy(s3status)
    with io.open(logpath,"wb") as writer, io.open(logpath,"rb",1) as reader:
        starttime = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        process = subprocess.Popen(command,stdout = writer,stderr = writer)
        ## initialize a legacy logging object. starttime
        while process.poll() is None:
            sys.stdout.write(reader.read().decode("utf-8"))
            ncds.update_file(logpath,starttime)
            ncds.write()
            time.sleep(0.5)
            ## update logging. 
        sys.stdout.write(reader.read().decode("utf-8"))
        finishtime = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        ncds.update_file(logpath,starttime,finishtime,process.returncode)
        ncds.write()
        ## finish logging, get end log time + exit code. 
    return process.returncode    

class NeuroCAASScriptManager(object):
    """An object to take care of the management logic of handling input/output and logging on a NeuroCAAS job. Has all of its state stored in a json file called "registration.json" in the io-dir folder where job inputs and outputs are kept. 

    """
    def __init__(self,path):
        """Initialize the script manager with a location where we will keep all of its data.

        """



## cli tools. 
def register_data(s3_datapath):
    """Register the dataset. Get the dataset name and local path, and write it to a persistent file stored at "configpath".  

    """
    try:
        with open(configpath,"r") as f:
            dataconfig  = json.load(f)
    except FileNotFoundError:        
        dataconfig = {}
    dataconfig["datapath"] = s3_datapath 
    with open(configpath,"w") as f:
        json.dump(dataconfig,f)
    print("Registered dataset: {}".format(s3_datapath))    

def register_config(s3_configpath):
    """Register the config file to use. Get the config name and local path, and write it to a persistent file stored at "configpath".

    """
    try:
        with open(configpath) as f:
            dataconfig  = json.load(f)
    except FileNotFoundError:        
        dataconfig = {}
    dataconfig["configpath"] = s3_configpath 
    with open(configpath,"w") as f:
        json.dump(dataconfig,f)
    print("Registered config file: {}".format(s3_configpath))    

def get_dataset_name():
    """ Get the name of the registered dataset. 

    """
    try:
        with open(configpath) as f:
            dataconfig = json.load(f)
        datapath = dataconfig["datapath"]    
    except Exception:    
        print("Registered dataset not found.")
        raise
    
    return os.path.basename(datapath)
    
def get_config_name():
    """ Get the name of the registered config. 

    """
    try:
        with open(configpath) as f:
            dataconfig = json.load(f)
        configpath = dataconfig["configpath"]    
    except Exception:    
        print("Registered config file not found.")
        raise
    
    return os.path.basename(configpath)

def get_group_name(path = None):
    """Get the name of the group identified with registered data nad config. If not consistent, you must specify path as "data" or "config"
    :param path: (optional) must be data or config if given to specify where data is taken from. 

    """
    pass

def get_bucket_name(path = None):
    """Get the name of the bucket 

    """

def get_datastatus_name(custom=None):   
    """Get the datastatus name by formatting the dataset name. Can have a custom name to format instead if desired. 

    """
    
