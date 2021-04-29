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
from .log import NeuroCAASCertificate,NeuroCAASDataStatus,NeuroCAASDataStatusLegacy
from .Interface_S3 import download,upload

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

def mkdir_notexists(dirname):
    if not os.path.isdir(dirname):
        os.makedirs(dirname)

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
    def __init__(self,path,write = True):
        """Initialize the script manager with a location where we will keep all of its data.
        Creates a file "registration.json" at that location. 
        This file contains a field to register 
        :param path: path to the directory where we will write the file registration.json
        :param write: boolean, if we should write the file or not. Useful if initializing from existing class. 

        """
        assert os.path.isdir(path); "Must give path to existing input/output directory"
        self.path = path
        ## The subdirectories to expect/create at the given location. 
        self.subdirs = {"data":"inputs","config":"configs","results":"results","logs":"logs"}
        self.pathtemplate = {"s3":None,"local":None}
        self.registration = {
                "data":{k:v for k,v in self.pathtemplate.items()},
                "config":{k:v for k,v in self.pathtemplate.items()},
                "additional_files":{}
                }

        if write is True:
            self.write()

    def write(self):        
        with open(os.path.join(self.path,"registration.json"),"w") as reg: 
            json.dump(self.registration,reg)

    @classmethod
    def from_registration(cls,path):       
        """If a registration file "registration.json" already exists at a given location, initialize from this file.   

        """
        assert os.path.isdir(path); "Must give path to existing input/output directory"
        try:
            with open(os.path.join(path,"registration.json"),"r") as reg:
                registration = json.load(reg)
        except FileNotFoundError:        
            raise FileNotFoundError("no registration found at this location.")

        inst = cls(path,write = False)
        inst.registration = registration
        return inst

    def register_data(self,s3path):
        """Given an s3 path, registers that as the location of the data we care about. 
        :param s3path: path to a file in aws s3, given in "s3://bucket/path" format

        """
        ## canc check existence later. 
        self.registration["data"]["s3"] = s3path
        self.write()

    def register_config(self,s3path):
        """Given an s3 path, registers that as the location of the data we care about. 
        :param s3path: path to a file in aws s3, given in "s3://bucket/path" format

        """
        ## canc check existence later. 
        self.registration["config"]["s3"] = s3path
        self.write()

    def register_file(self,name,s3path):
        """Given an s3 path, registers that as the location of the data we care about. 
        :param name: name of the file to register this data path under.  
        :param s3path: path to a file in aws s3, given in "s3://bucket/path" format

        """
        ## initialize
        self.registration["additional_files"][name] = {k:v for k,v in self.pathtemplate.items()} 
        ## populate
        self.registration["additional_files"][name]["s3"] = s3path
        self.write()

    def get_data(self,path = None,force = False,display = False):    
        """Get currently registered data. If desired, you can pass a path where you would like data to be moved. Otherwise, it will be moved to self.path/self.subdirs[data]
        :param path: (optional) the location you want to write data to. 
        :param force: (optional) by default, will not redownload if data of the same name already lives here. Can override with force = True
        :param display: (optional) by default, will not display downlaod progress. 

        """
        try:
            data_s3path = self.registration["data"]["s3"]
            assert data_s3path is not None
            data_name = os.path.basename(data_s3path)
        except AssertionError:     
            raise AssertionError("Data not registered. Run register_data first.") 

        if path is None: 
            path = os.path.join(self.path,self.subdirs["data"])
            mkdir_notexists(path)
        data_localpath = os.path.join(path,data_name)

        if not force: 
            assert not os.path.exists(data_localpath), "Data already exists at this location. Set force = true to overwrite"
        download(data_s3path,data_localpath)    

            
    def get_config(self,path = None,force = False,display = False):    
        """Get currently registered config. If desired, you can pass a path where you would like config to be moved. Otherwise, it will be moved to self.path/self.subdirs[config]
        :param path: (optional) the location you want to write data to. 
        :param force: (optional) by default, will not redownload if config of the same name already lives here. Can override with force = True
        :param display: (optional) by default, will not display downlaod progress. 

        """
        try:
            config_s3path = self.registration["config"]["s3"]
            assert config_s3path is not None
            config_name = os.path.basename(config_s3path)
        except AssertionError:     
            raise AssertionError("Config not registered. Run register_config first.") 

        if path is None: 
            path = os.path.join(self.path,self.subdirs["config"])
            mkdir_notexists(path)
        config_localpath = os.path.join(path,config_name)

        if not force: 
            assert not os.path.exists(config_localpath), "Data already exists at this location. Set force = true to overwrite"
        download(config_s3path,config_localpath)    

    def get_file(self,filename,path = None,force = False,display = False):    
        """Get currently registered file. If desired, you can pass a path where you would like file to be moved. Otherwise, it will be moved to self.path/self.subdirs[data]
        :param path: (optional) the location you want to write data to. 
        :param force: (optional) by default, will not redownload if file of the same name already lives here. Can override with force = True
        :param display: (optional) by default, will not display downlaod progress. 

        """
        try:
            file_s3path = self.registration["additional_files"][filename]["s3"]
        except KeyError:    
            raise AssertionError("File not registered. Run register_file first.") 
        try:
            assert file_s3path is not None
            file_name = os.path.basename(file_s3path)
        except AssertionError:     
            raise AssertionError("Config not registered. Run register_file first.") 

        if path is None: 
            path = os.path.join(self.path,self.subdirs["data"])
            mkdir_notexists(path)
        file_localpath = os.path.join(path,file_name)

        if not force: 
            assert not os.path.exists(file_localpath), "Data already exists at this location. Set force = true to overwrite"
        download(file_s3path,file_localpath)    
         
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
    
