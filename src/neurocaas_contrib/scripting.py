## module for scripting tools. 
import os
import io
import shutil
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
    archive.extractall(path = path,members = filtered_namelist) ## This should extract and replace. Maybe it does so at the file level
    return folder.pop()

## from https://stackoverflow.com/questions/18421757/live-output-from-subprocess-command
def log_process(command,logpath,s3status):
    """Given a path to an executable, runs it, logs output and prints to stdout. 

    :param processpath: command you want to run. 
    :param logpath: path where you will log the stdout/err outputs locally. 
    :param s3status: s3 path where the dataset is stored  
    :return: return code of the command. 
    """
    ## Initialize datastatus object. 
    ncds = NeuroCAASDataStatusLegacy(s3status)
    ## Initialize certificate object. 
    s3certificate = os.path.join(os.path.dirname(s3status),"certificate.txt")
    localcertificate = os.path.join(os.path.dirname(logpath),"certificate.txt")
    ncc = NeuroCAASCertificate(s3certificate,localcertificate)
    dataname = os.path.basename(ncds.rawfile["input"])
    updatedict = {
        "t" : datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S"),
        "n" : dataname,
        "s" : ncds.rawfile["status"],
        "r" : "N/A",
        "u" : "N/A",
    }
    ncc.update_instance_info(updatedict)
    with io.open(logpath,"wb") as writer, io.open(logpath,"rb",1) as reader:
        starttime = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        process = subprocess.Popen(command,stdout = writer,stderr = writer)
        ## initialize a legacy logging object. starttime
        sys.stdout.write("\n\n-------Start Process Log-------\n\n")
        while process.poll() is None:
            stdlatest = reader.read().decode("utf-8")
            sys.stdout.write(stdlatest)
            ncds.update_file(logpath,starttime)
            ncds.write()
            updatedict["t"] = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
            updatedict["s"] = ncds.rawfile["status"]
            updatedict["r"] = stdlatest.replace("\n"," ")
            updatedict["u"] = ncds.rawfile["cpu_usage"]
            ncc.update_instance_info(updatedict)
            ncc.write()
            time.sleep(0.5)
            ## update logging. 
            
        stdlast = reader.read().decode("utf-8")
        sys.stdout.write(stdlast)
        sys.stdout.write("\n--------End Process Log--------\n\n")
        finishtime = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        ncds.update_file(logpath,starttime,finishtime,process.returncode)
        ncds.write()
        updatedict["t"] = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S") + " (finished)"
        updatedict["s"] = ncds.rawfile["status"]
        updatedict["r"] = stdlast.replace("\n"," ")
        updatedict["u"] = ncds.rawfile["cpu_usage"]
        ncc.update_instance_info(updatedict)
        ncc.write()
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
        #self.pathtemplate = {"s3":None,"localsource":None,"local":None}
        self.registration = {
                "data":{},
                "config":{},
                "additional_files":{},
                "resultpath":{}
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
        assert str(s3path).startswith("s3://"), "must be given in s3 form"
        self.registration["data"]["s3"] = str(s3path)
        self.registration["data"].pop("localsource","False")
        self.registration["data"].pop("local","False")
        self.write()

    def register_data_local(self,localpath):
        """Given a local path, registers that as the location of the data we care about. 
        :param localpath: path to a file on the machine itself. 

        """
        ## canc check existence later. 
        self.registration["data"]["localsource"] = str(localpath)
        self.registration["data"].pop("s3","False")
        self.registration["data"].pop("local","False")
        self.write()

    def register_config(self,s3path):
        """Given an s3 path, registers that as the location of the data we care about. 
        :param s3path: path to a file in aws s3, given in "s3://bucket/path" format

        """
        ## canc check existence later. 
        assert str(s3path).startswith("s3://"), "must be given in s3 form"
        self.registration["config"]["s3"] = str(s3path)
        self.registration["config"].pop("localsource","False")
        self.registration["config"].pop("local","False")
        self.write()

    def register_config_local(self,localpath):
        """Given a local path, registers that as the location of the config file we care about. 
        :param localpath: path to a file on the machine itself. 

        """
        ## canc check existence later. 
        self.registration["config"]["localsource"] = str(localpath)
        self.registration["config"].pop("s3","False")
        self.registration["config"].pop("local","False")
        self.write()

    def register_file(self,name,s3path):
        """Given an s3 path, registers that as the location of a file we care about. 
        :param name: name of the file to register this data path under.  
        :param s3path: path to a file in aws s3, given in "s3://bucket/path" format

        """
        assert str(s3path).startswith("s3://"), "must be given in s3 form"
        ## initialize
        #self.registration["additional_files"][name] = {k:v for k,v in self.pathtemplate.items()} 
        self.registration["additional_files"][name] = {} 
        ## populate
        self.registration["additional_files"][name]["s3"] = str(s3path)
        self.registration["additional_files"][name].pop("localsource","False")
        self.registration["additional_files"][name].pop("local","False")
        self.write()

    def register_file_local(self,name,localpath):
        """Given a local path, registers that as the location of a file we care about. 
        :param name: name of the file to register this data path under.  
        :param localpath: path to a file on the machine itself. 

        """
        ## initialize
        #self.registration["additional_files"][name] = {k:v for k,v in self.pathtemplate.items()} 
        self.registration["additional_files"][name] = {} 
        ## populate
        self.registration["additional_files"][name]["localsource"] = str(localpath)
        self.registration["additional_files"][name].pop("s3","False")
        self.registration["additional_files"][name].pop("local","False")
        self.write()

    def register_resultpath(self,s3path):    
        """Given an s3 path, registers that as the location where we will upload job data. Give a folder, where you want to generate two subdirectories, "logs", and "process_results". Logs and analysis results will be sent to these respective locations.  

        """
        assert s3path.startswith("s3://"), "must be given in s3 form"
        self.registration["resultpath"]["s3"] = str(s3path)
        self.registration["resultpath"].pop("localsource","False")
        self.write()

    def register_resultpath_local(self,localpath):    
        """Given an local path, registers that as the location where we will upload job data. Give a folder, where you want to generate two subdirectories, "logs", and "process_results". Logs and analysis results will be sent to these respective locations.  

        """
        self.registration["resultpath"]["localsource"] = str(localpath)
        self.registration["resultpath"].pop("s3","False")
        self.write()

    def get_data(self,path = None,force = False,display = False):    
        """Get currently registered data. If desired, you can pass a path where you would like data to be moved. Otherwise, it will be moved to self.path/self.subdirs[data]
        :param path: (optional) the location you want to write data to. 
        :param force: (optional) by default, will not redownload if data of the same name already lives here. Can override with force = True
        :param display: (optional) by default, will not display downlaod progress. 
        :return: bool (True if downloaded, False if not)

        """
        try:
            data_s3path = self.registration["data"]["s3"]
            data_name = os.path.basename(data_s3path)
            source = "s3"
        except KeyError:     
            try:
                data_localsource = self.registration["data"]["localsource"]
                data_name = os.path.basename(data_localsource)
                source = "local"
            except:    
                raise AssertionError("Data not registered. Run register_data first.") 

        if path is None: 
            path = os.path.join(self.path,self.subdirs["data"])
            mkdir_notexists(path)
        data_localpath = os.path.join(path,data_name)

        if not force: 
            if os.path.exists(data_localpath):
                print("Data already exists at this location. Set force = true to overwrite")
                return 0
            else:   
                pass
        if source == "s3":   
            download(data_s3path,data_localpath,display)    
        elif source == "local":   
            shutil.copy(data_localsource,data_localpath)
        self.registration["data"]["local"] = data_localpath
        self.write()
        return 1

    def get_config(self,path = None,force = False,display = False):    
        """Get currently registered config. If desired, you can pass a path where you would like config to be moved. Otherwise, it will be moved to self.path/self.subdirs[config]
        :param path: (optional) the location you want to write data to. 
        :param force: (optional) by default, will not redownload if config of the same name already lives here. Can override with force = True
        :param display: (optional) by default, will not display downlaod progress. 
        :return: bool (True if downloaded, False if not)

        """
        try:
            config_s3path = self.registration["config"]["s3"]
            config_name = os.path.basename(config_s3path)
            source = "s3"
        except KeyError:     
            try:
                config_localsource = self.registration["config"]["localsource"]
                config_name = os.path.basename(config_localsource)
                source = "local"
            except:    
                raise AssertionError("Config not registered. Run register_config first.") 

        if path is None: 
            path = os.path.join(self.path,self.subdirs["config"])
            mkdir_notexists(path)
        config_localpath = os.path.join(path,config_name)

        if not force: 
            if os.path.exists(config_localpath):
                print("Config already exists at this location. Set force = true to overwrite")
                return 0 
            else:   
                pass
        if source == "s3":    
            download(config_s3path,config_localpath,display)    
        elif source == "local":    
            shutil.copy(config_localsource,config_localpath)
        self.registration["config"]["local"] = config_localpath
        self.write()
        return 1


    def get_file(self,varname,path = None,force = False,display = False):    
        """Get currently registered file. If desired, you can pass a path where you would like file to be moved. Otherwise, it will be moved to self.path/self.subdirs[data]
        :param varname: name of the file key in the registration dictionary.  
        :param path: (optional) the location you want to write data to. 
        :param force: (optional) by default, will not redownload if file of the same name already lives here. Can override with force = True
        :param display: (optional) by default, will not display downlaod progress. 
        :return: bool (True if downloaded, False if not)

        """
        try:
            file_s3path = self.registration["additional_files"][varname]["s3"]
            file_name = os.path.basename(file_s3path)
            source = "s3"
        except KeyError:    
            try:
                file_localsource = self.registration["additional_files"][varname]["localsource"]
                file_name = os.path.basename(file_localsource)
                source = "local"
            except:    
                raise AssertionError("File not registered. Run register_file first.") 

        if path is None: 
            path = os.path.join(self.path,self.subdirs["data"])
            mkdir_notexists(path)
        file_localpath = os.path.join(path,file_name)

        if not force: 
            if os.path.exists(file_localpath):
                print("Config already exists at this location. Set force = true to overwrite")
                return 0
            else:   
                pass
        if source == "s3":    
            download(file_s3path,file_localpath,display)    
        elif source == "local":    
            shutil.copy(file_localsource,file_localpath)
        self.registration["additional_files"][varname]["local"] = file_localpath
        self.write()
        return 1

    def put_result(self,localfile,display = False):
        """
        :param localfile: the location you want to write data from. 
        :param display: (optional) by default, will not display upload progress. 
        :return: bool (True if uploaded, False if not)
        """
        filename = os.path.basename(localfile)
        try:
            fullpath = os.path.join(self.registration["resultpath"]["s3"],"process_results",filename)
            upload(localfile,fullpath,display)
        except KeyError: 
            try:
                fullpath = os.path.join(self.registration["resultpath"]["localsource"],"process_results",filename)
                os.makedirs(os.path.dirname(fullpath),exist_ok = True)
                shutil.copy(localfile,fullpath)
            except:    
                raise AssertionError("Result location not registered. Run register_resultpath first.")

    def get_name(self,contents):
        """Given a generic dictionary of structure self.pathtemplate, correctly returns the filename if available. 
        :param contents: a dictionary of structure {"s3":location,"local":location}
        """
        assert contents["local"] is not None, "local path does not exist."
        return os.path.basename(contents["local"])

    def get_group(self,contents):
        """Given a generic dictionary of structure self.pathtemplate, correctly returns the filename if available. 
        :param contents: a dictionary of structure {"s3":location,"local":location}
        """
        assert contents["s3"] is not None, "s3 path does not exist. "
        bucketname, groupname, subkey = contents["s3"].split("s3://")[-1].split("/",2)
        return groupname 

    def get_path(self,contents):
        """Given a generic dictionary of structure self.pathtemplate, correctly returns the local filepath if available. 
        :param contents: a dictionary of structure {"s3":location,"local":location}
        """
        assert contents["local"] is not None, "local path does not exist. "
        return contents["local"]

    def get_dataname(self):
        """Get name of data

        """
        return self.get_name(self.registration["data"]) 

    def get_dataname_remote(self):
        """Get name of data

        """
        return self.registration["data"]["s3"] 

    def get_configname(self):
        """Get name of config

        """
        return self.get_name(self.registration["config"]) 

    def get_filename(self,varname):
        """Get name of file

        """
        return self.get_name(self.registration["additional_files"][varname]) 

    def get_datapath(self):
        """Get path of data

        """
        return self.get_path(self.registration["data"]) 

    def get_configpath(self):
        """Get path of config

        """
        return self.get_path(self.registration["config"]) 

    def get_filepath(self,varname):
        """Get path of file

        """
        return self.get_path(self.registration["additional_files"][varname]) 
    
    def get_resultpath(self,filepath):
        """Given the path to a file or directory locally, give the path we would upload it to in S3 (useful for using aws s3 sync)

        """
        assert self.registration["resultpath"] is not None, "result path must be registered"
        basename = os.path.basename(os.path.normpath(filepath))
        try:
            resultpath =  os.path.join(self.registration["resultpath"]["s3"],"process_results",basename)
        except KeyError:    
            try:
                resultpath =  os.path.join(self.registration["resultpath"]["localsource"],"process_results",basename)
            except KeyError:    
                raise KeyError("Not registered.")
        return resultpath    

    def log_command(self,command,s3log,path=None):
        """Wrapper around bare log_process function to provide the local logpath. 
        :param path: path to a directory where you want to write the log outputs to tmplog.txt

        """
        if path is None: 
            path = os.path.join(self.path,self.subdirs["logs"])
            mkdir_notexists(path)
        log_process(command,os.path.join(path,"log.txt"),s3log)    

    def cleanup(self):    
        """Indicates the end of registered workflow. Sends the relevant config file to the results directory, and sends a file called "update.txt" as well.

        """
        ## get config file to another loc: 
        resultpath = os.path.join(self.path,self.subdirs["logs"])
        assert self.get_config(path = resultpath)
        configpath = self.get_configpath()
        loadpath = os.path.join(os.path.dirname(configpath),"update.txt")
        self.put_result(configpath)
        with open(os.path.join(loadpath),"w") as f: 
            f.close()
        self.put_result(loadpath)


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
    
