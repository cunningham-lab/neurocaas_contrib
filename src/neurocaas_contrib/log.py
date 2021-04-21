import datetime
import subprocess
import shlex
from collections import OrderedDict
import pdb
import re
import json
import os
import docker
import sys
import boto3
from urllib.parse import urlparse
from botocore.exceptions import ClientError
import traceback

filepath = os.path.realpath(__file__)
client = docker.from_env()

s3_resource = boto3.resource("s3")
divider = "================"
localdata_dict = {
        "certificate_base":os.path.join(os.path.dirname(filepath),"template_mats/certificate.txt"),
        "certificate_update":os.path.join(os.path.dirname(filepath),"template_mats/certificate_update.txt"),
        "datastatus_base":os.path.join(os.path.dirname(filepath),"template_mats/DATASET_NAME-dataset.ext_STATUS.txt.json"),
        "datastatus_update":os.path.join(os.path.dirname(filepath),"template_mats/DATASET_NAME-dataset_update.ext_STATUS.txt.json")

        }
localdatapath = os.path.join(os.path.dirname(filepath),"template_mats/certificate.txt")
localdatapath_update = os.path.join(os.path.dirname(filepath),"template_mats/certificate_update.txt")

def find_linebreaks(tup):
    
    """
    Finds part of the file indicating the per-dataset log. 
    args: 
    :param tup: tuple where the first element is an index and the second is the corresponding line of a text file. Compares against global variable "divider" to find linebreaks 
    """
    return tup[1] == divider

def load_file_s3(bucket_name, key):
    """ """
    try:
        file_object = s3_resource.Object(bucket_name, key)
        raw_content = file_object.get()['Body'].read() 
    except ValueError as ve:
        print("Error loading config file. Error is: {}".format(ve))
        raise ValueError
    except ClientError as ce:
        e = ce.response["Error"]["Code"]
        print("Encountered AWS Error: {}".format(e))
        raise ValueError
    return raw_content.decode("utf-8")

class WriteObj(object):
    """Wrapper to handle cases where we want to write to local or to s3. If s3, acts like an s3 resource object. If local, acts like a standard file object.

    """
    def __init__(self,init_dict):
        """Initialization determines whether we will write to local or remote. The init_dict should have the following format: 
        {
            loc:["s3","local"],
            localpath:"path/to/local.txt",
            bucket:"bucketname",
            key:"key"
        }
        :param init_dict: Initialization dictionary. If loc = s3, bucket and key parameters are required. If loc = local, localpath is required. 
        """
        assert init_dict["loc"] in ["s3","local"], "Location argument must be 's3' or 'local'"
        self.init_dict = init_dict
        if self.init_dict["loc"] is "s3":
            assert self.init_dict.get("bucket",False) and self.init_dict.get("key","False"),"Params bucket,key must be specified. "
        elif self.init_dict["loc"] is "local":
            assert self.init_dict.get("localpath",False),"Param localpath must be specified. "

    def put(self,stringbody): 
        """String to put at the object represented by this instance. 

        :param stringbody: a string representing the body of this object.
        """
        if self.init_dict["loc"] == "s3":
            writeobj = s3_resource.Object(self.init_dict["bucket"],self.init_dict["key"])
            writeobj.put(Body=stringbody.encode("utf-8"))
        elif self.init_dict["loc"] == "local":
            with open(self.init_dict["localpath"],"wb") as f:
                f.write(stringbody.encode("utf-8"))

    def put_json(self,dictbody): 
        """String to put at the object represented by this instance. 

        :param dictbody: a dictionary representing the body of this object.
        """
        if self.init_dict["loc"] == "s3":
            writeobj = s3_resource.Object(self.init_dict["bucket"],self.init_dict["key"])
            writeobj.put(Body=json.dumps(dictbody).encode("utf-8"))
        elif self.init_dict["loc"] == "local":
            with open(self.init_dict["localpath"],"w") as f:
                json.dump(dictbody,f,indent = 4)
       
class NeuroCAASLogObject(object):
    """Abstract base class for logging objects. Defines an init method that does the following:   
    1. looks for an initialization file from Amazon S3. 
    2. if file is available, uses it to initialize internal information. The object will write updates back to this same file.
    3. if file is not available, initializes from a local source. The object will write back to the file specified at the path given in parameter write_localpath. 
    This init behavior also determines the initialization of a writeobject that will write to s3 (back to the same file given to initialize) or a local filepath. This local fallback ensures that we don't lose valuable logging info in cases where processes are being run locally.

    """
    def __init__(self,s3_path,write_localpath):
        """Constructor method. 

        :param s3_path: the path to an s3 object, given as an s3 uri (s3://bucketname/keyname). 
        :param write_localpath: the localpath that we will write to. This should be passed defaults from global variables declared in this module. 

        """
        self.logtype = type(self).__name__
        self.validate_path(s3_path)
        writeobj_dict = {
                "loc":None,
                "bucket":None,
                "key":None,
                "localpath":write_localpath
                }
        try:
            uriparse = urlparse(s3_path,allow_fragments=False)
            bucket_name = uriparse.netloc
            path = uriparse.path.lstrip("/")
            rawfile = self.load_init_s3(bucket_name,path)
            #rawcert = load_cert(bucket_name,path)
            self.rawfile = rawfile
            #self.rawcert = rawcert
            writeobj_dict["loc"] = "s3"
            writeobj_dict["bucket"] = bucket_name
            writeobj_dict["key"] = path
            self.writeobj = WriteObj(writeobj_dict)
        except:
            e = traceback.format_exc()
            #print("Error getting certificate, not formatted for per-job logging. Message: {}\nLoading default certificate from local instead. Updates will be logged to file {}".format(e,write_localpath))
            print(f"Error getting {self.logtype} object, not connecting to remote. Loading default {self.logtype} template from local instead.") 
            #print("Updates will be logged to file {}".format(write_localpath))
            rawfile = self.get_default_rawfile()
            self.rawfile = rawfile
            writeobj_dict["loc"] = "local"
            self.writeobj = WriteObj(writeobj_dict)

    def validate_path(self,s3_path):
        """Validates that the path given is a correctly formatted S3 URI.
        """
        assert s3_path.startswith("s3://"), "s3_path must be given as s3 URI (starts with s3://)"

    def load_init_s3(self,bucketname,path):
        """Load in file to use as initialization for this logging object.   
        :param bucketname: The name of the s3 bucket we are reading from.
        :param path: The name of the key within the s3 bucket corresponding to the initialization object. 
        :return: Return the content of the s3 file without further processing. 
        """
        raise NotImplementedError()

    def get_default_rawfile(self):
        """In the case that the object designated in s3 is not avaiable, get one from a local storage location.  
        :return: Return the content of a default file to initialize with. Should be of the same type as the output of load_init_s3.
        """
        raise NotImplementedError()

class NeuroCAASCertificate(NeuroCAASLogObject):
    """Per-submission log file that captures the setup of resources on neurocaas, and provides basic summary information about each instance started by the job as it runs. Captures the git commit of the neurocaas blueprint version to ensure reproducibility. 

    """
    def __init__(self,s3_path,write_localpath=localdata_dict["certificate_update"]):
        """Given an s3 uri to a certificate file, initializes from that certificate file. If not given or not accessible/ load in a default certificate and fill in as we go (some information will be missing)

        :param s3_path: the path to an s3 object, given as an s3 uri (s3://bucketname/keyname). 
        :param write_localpath: the localpath that we will write to. This should be passed defaults from global variables declared in this module. 

        """
        super().__init__(s3_path,write_localpath)
        self.assign_template()
        self.certdict,self.writedict,self.writearea = self.process_rawcert(self.rawfile)

    def load_init_s3(self,bucketname,path):
        """Load in file to use as initialization for this logging object.   
        :param bucketname: The name of the s3 bucket we are reading from.
        :param path: The name of the key within the s3 bucket corresponding to the initialization object. 
        :return: Return the content of the s3 file without further processing. 
        """
        content = load_file_s3(bucketname,path)
        return content

    def assign_template(self):
        """Assigns template strings to allow for easy fill in of certificate updates..  
        """
        self.dataset_template = "DATANAME: {n} | STATUS: {s} | TIME: {t} | LAST COMMAND: {r} | CPU_USAGE: {u}"

    def get_default_rawfile(self):
        """Get the default certificate from a local location. This ensures we can continue with processing even when the job is not launched from remote. 

        :return: raw certificate file.
        """
        with open(localdata_dict["certificate_base"],"r") as f:
            rawcert = f.read()
        return rawcert 
        
    def process_rawcert(self,cert):
        """Takes the raw certificate and preprocesses it for easier handling. In particular, separates it into line breaks, identifies the parts of the file that we should write to, and identifies individual lines by their corresponding data. Will assign values to the self.certlines and self.writedict attributes. 

        :param cert: raw data containing certificate file.
        :return: tuple (certdict, writedict, writearea) of dictionaries and a range object. First entry has line numbers as keys and content of those lines as values.Second entry has line numbers as keys, and a dictionary of format {"dataname":dataname,"line":text} as value. Third entry indicates the range of lines where we can write. 
        """
        certlines = self.rawfile.split("\n")
        certdict = {ci:cl for ci,cl in enumerate(certlines)}
        linebreak_locs = dict(filter(find_linebreaks,certdict.items()))
        assert len(linebreak_locs) == 2,"This divider should indicate only the start and end of the actively updated status." 
        interval = sorted(linebreak_locs.keys())
        writearea = range(interval[0]+1,interval[1])
        writedict = {}
        for i in writearea:
            text = certdict[i]
            m = re.search(r'DATANAME: (.*?) |',text)
            if m.group(1) is not None:
                dataname = m.group(1)
            else:    
                dataname = "groupname/inputs/dataname.ext"
            writedict[dataname] = {"linenb":i,"dataname":dataname,"line":text} 
        return (certdict,writedict,writearea)

    def update_instance_info(self,updatedict,loc=0):
        """Updates the info on an instance in the certificate. Update takes the form of a dictionary, with the following entries, where all values are strings.:
        {
            "n": datasetname,
            "s": job status (INITIALIZING, IN PROGRESS, FAILED, SUCCESS),
            "t": time of last update,
            "r": last command run,
            "u": CPU usage
        }
        If any of these entries are not given they are set to N/A. 
        Additionally, the location in the certificate where these values should be written will be inferred from the provided dataset name: i.e., if there are multiple instances being tracked by the certificate file at once, we need to know which one write this data to. If no dataset name is provided, we fall back to writing on the line indexed by the variable "loc", which is given relative to all writable lines. 

        :param updatedict: A dictionary giving the values to update individual parameters. 
        :param loc: (optional) The relative line number that this update should be written to. Default is 0.
        """
        ## First filter the given keys, and determine if any are missing:
        given_keys = updatedict.keys()
        all_keys = ["n","s","t","r","u"]
        for key in given_keys:
            assert key in all_keys
        for key in all_keys:
            if key not in given_keys:
                updatedict[key] = "N/A"
        formatted = self.dataset_template.format(**updatedict)
        ## Now determine where to write this:
        datainfo_given = self.writedict.get(updatedict["n"],False)
        try:
            if datainfo_given is False:
                write_index = self.writearea[loc]
            else: 
                write_index = self.writedict[datainfo_given["dataname"]]["linenb"]
            self.certdict[write_index] = formatted  
        except IndexError:
            raise IndexError("The argument loc you gave is not compatible with the certificate (not in write area)")

    def initialize_writeobj(self,mode,bucket=None,path=None,localpath=None): 
        """Method to initialize the WriteObj object passed to self.writeobj. Determines if we are writing to s3 (as in service mode) or to a local location (debugging). Note that if mode is local, bucket and path arguments are not required, and vice versa for s3 and localpath. However if they are not included for a particular mode an error will be thrown.

        :param mode: processing mode; either "local" or "s3". Will initiaize   
        :param bucket:(optional) name of the s3 bucket to write to. Will not be used if mode is local, but  
        :param path:(optional) make of the key in the s3 bucket indicated to write to.
        :param path:(optional) make of the key in the s3 bucket indicated to write to.

        """
        assert mode in ["local","s3"],"parameter mode must be 'local' or 's3'"

        #self.writeobj = WriteObj({"loc":"s3","bucket":bucket_name,"key":path})

    def write(self):    
        """Writes the contents of the file as dictated by the self.writeobj attribute. If writeobj is s3 (default), the updated certificate will be written to the path at self.s3_path. If not (s3 not reachable for any reason) will be written to the file ./template_mats/certificate_update.txt for inspection. If you intend to write to a different file location, use the method write_local instead. 

        """
        ## First sort lines:
        sort_line_tuples = sorted(self.certdict.items(),key = lambda x: x[0])
        sorted_lines = [s[1] for s in sort_line_tuples]
        body = "\n".join(sorted_lines)
        self.writeobj.put(body)

    def write_local(self,path):    
        """Writes the contents of the file as dictated by the self.writeobj attribute locally. 

        :param path: Local path where we should write the contents of this file. 
        """
        ## First sort lines:
        sort_line_tuples = sorted(self.certdict.items(),key = lambda x: x[0])
        sorted_lines = [s[1] for s in sort_line_tuples]
        body = "\n".join(sorted_lines)
        with open(path, "wb") as f:
            f.write(body.encode("utf-8"))

class NeuroCAASDataStats(NeuroCAASLogObject):
    """Base class for original and docker based DataStatus log objects. 

    """
        
    def load_init_s3(self,bucketname,path):
        """Load in file to use as initialization for this logging object. Should be a dictionary.   
        :param bucketname: The name of the s3 bucket we are reading from.
        :param path: The name of the key within the s3 bucket corresponding to the initialization object. 
        :return: Return the content of the s3 file without further processing (will be a dictionary). 
        """
        content = json.loads(load_file_s3(bucketname,path))
        return content

    def get_default_rawfile(self):
        """Get the default dataset status file from a local location. This ensures we can continue with processing even when the job is not launched from remote. For this analysis, this file is a dictionary. 

        :return: raw certificate file .
        """
        with open(localdata_dict["datastatus_base"],"r") as f:
            rawfile = json.load(f)
        return rawfile 

        
    def write(self):    
        """Writes the contents of rawfile as dictated by the self.writeobj attribute. Will sort entries with an ordereddict according to the attribute self.writeorder. If writeobj is s3 (default), the updated certificate will be written to the path at self.s3_path. If not (s3 not reachable for any reason) will be written to the file ./template_mats/certificate_update.txt for inspection. If you intend to write to a different file location, use the method write_local instead. 

        """
        ## First sort entries:
        od = OrderedDict([
               (key,self.rawfile[key]) for key in self.writeorder])
        self.writeobj.put_json(od)

    def write_local(self,path):    
        """Writes the contents of the file as dictated by the self.writeobj attribute to a local file. First, will sort keys with the "self.writeorder" flag. 

        :param path: Local path where we should write the contents of this file. 
        """
        ## First sort entries:
        od = OrderedDict([
               (key,self.rawfile[key]) for key in self.writeorder])
        with open(path, "w") as f:
            json.dump(od,f,indent = 4)

class NeuroCAASDataStatusLegacy(NeuroCAASDataStats):
    """Per-instance log file that captures details about data analyses. Captures stdout/err, exit code, error info, and available information, but does not assume docker based deployment. 
    :param dataset_name: name of the dataset this status object is tracking. 
    :param suffix: any changes to the name of the dataset you want to make. 
    """
    def __init__(self,s3_path,write_localpath=localdata_dict["datastatus_update"]):
        ## This is the order in which the json file's elements should be listed.
        self.writeorder = [
                   "instance",
                   "command",
                   "input",
                   "status",
                   "reason",
                   "memory_usage",
                   "cpu_usage",
                   "job_start",
                   "job_finish",
                   "std"]
        ## Initialize the cpu usage stats with 0 
        self.prev_cpu = 0
        self.prev_system = 0

        super().__init__(s3_path,write_localpath)

    def get_stdout(self,filename):
        """Assumes stdout/err are already routed to an existing file. Reads in from that file, line by line

        """
        with open(filename,"r") as f:
            lines = f.readlines()
        return lines    

    def get_usage(self):    
        """Outputs usage statistics for the machine as a whole .
        :returns: Output dictionary with the following form:
            outdict = {
            "cpu_total":cpu_percent,
            "memory_total_mb":memory_total_mb
            }
        """        
        cpu = subprocess.check_output(shlex.split("echo $[100-$(vmstat 1 2|tail -1|awk '{print $15}')]"))
        memory = "N/A" ## check this in linux. 
        outdict = {"cpu_total":cpu,
                "memory_total_mb":memory}
        return outdict

    def get_status(self,starttime,finishtime=None,exit_code=None):
        """Formats given status information as a dictionary.  
        :returns: dictionary of form: 
             { 
                 status:{"IN PROGRESS","SUCCESS","FAILED"},
                 starttime:{datetime}
                 endtime:{datetime,N/A}
                 error:{INT}
             }
        """
        custom_status = {}
        if exit_code is None:
            custom_status["status"] = "IN PROGRESS"
        elif exit_code == 0:     
            custom_status["status"] = "SUCCESS"
        else:    
            custom_status["status"] = "FAILED"

        custom_status["error"] = exit_code
        custom_status["starttime"] = starttime 
        if finishtime is None:
            custom_status["finishtime"] = "N/A"
        else:    
            custom_status["finishtime"] = finishtime 
        return custom_status    

    def update_file(self,stdfile,starttime,finishtime=None,exit_code=None):
        """Gets updates to status, usage, and stdout/err and aggregates them to be output together.   

        """
        writelines = self.get_stdout(stdfile)
        writedict = {str(i):line for i,line in enumerate(writelines)}
        statusdict = self.get_status(starttime,finishtime,exit_code)
        usage = self.get_usage()
        self.rawfile["status"] = statusdict["status"]
        self.rawfile["reason"] = statusdict["error"]
        self.rawfile["cpu_usage"] = "{} %".format(usage["cpu_total"])
        self.rawfile["memory_usage"] = "{} MB".format(usage["memory_total_mb"])
        self.rawfile["job_start"] = statusdict["starttime"]
        self.rawfile["job_finish"] = statusdict["finishtime"]
        self.rawfile["std"] = writedict
        ## Remove keys from legacy usage to avoid confusion
        for key in ["stderr","stdout"]:
            try:
                del self.rawfile[key]
            except KeyError:
                pass

class NeuroCAASDataStatus(NeuroCAASDataStats):
    """Per-instance log file that captures details about each individual dataset analysis run: entire history of messages printed to stdout/stderr, the exit code, any error information, etc. Written as a json file for convenience. Takes a running docker container and does everything needed to parse out relevant arguments from it. This includes the output to stdout and stderr, the current cpu usage and memory usage, the  docker container object that we will be querying for relevant status information. Note that this file is also assumed to be initialized by a lambda generated file, so we should treat it like the certificate file with similar failsafes to fall back on local processing. We inherit an init method from NeuroCAASLogObject to enable this. 

    :param dataset_name: name of the dataset this status object is tracking. 
    :param container: docker container object that we will be querying for relevant status information. 

    """
    def __init__(self,s3_path,container,write_localpath=localdata_dict["datastatus_update"]):
        ## This is the order in which the json file's elements should be listed.
        self.writeorder = [
                   "instance",
                   "command",
                   "input",
                   "status",
                   "reason",
                   "memory_usage",
                   "cpu_usage",
                   "job_start",
                   "job_finish",
                   "std"]
        ## Initialize the cpu usage stats with 0 
        self.prev_cpu = 0
        self.prev_system = 0

        super().__init__(s3_path,write_localpath)
        self.container = container

    def get_stdout(self):
        """Get the current output to container.logs() and format without escape characters.

        :returns: Most recent logs, formatted as a list of strings. 
        """
        ## Set up the way we will handle escape characters to format stdout:
        replacedict = {"\t":"    ","\r":""}
        logs = self.container.logs().decode("utf-8")
        for it in replacedict.items():
            logs = logs.replace(*it)
        logs_lines = logs.split("\n")    
        return logs_lines

    def get_usage(self):
        """Get the current usage information for the container. Unfortunately, docker does not itself calculate cpu percentages for you. We will take the raw, high level usage stats and return them as a dictionary.  
        NOTE: It's very difficult to find confirmation that these numbers are reported in bytes, but that is the assumption given the way that other commands (i.e. docker run) work. 

        :return: dictionary containing output statistics
        """
        current_usage_stats = json.loads(next(self.container.stats()).decode("utf-8"))
        ## Taken from https://github.com/TomasTomecek/sen/blob/master/sen/util.py#L175, itself taken from docker 
        cpu_usage = current_usage_stats["cpu_stats"]["cpu_usage"]["total_usage"]
        if cpu_usage is not 0:
            system_usage = current_usage_stats["cpu_stats"]["system_cpu_usage"]
            cpu_delta = cpu_usage - self.prev_cpu
            system_delta = system_usage - self.prev_system
            online_cpus = online_cpus = current_usage_stats["cpu_stats"].get("online_cpus", len(current_usage_stats["cpu_stats"]["cpu_usage"]["percpu_usage"]))
            cpu_percent = (cpu_delta/system_delta)*online_cpus*100
        else:
            cpu_percent = 0


        try:
            memory_total_stats = current_usage_stats["memory_stats"]["usage"]
            memory_total_mb = memory_total_stats/1e6
        except KeyError:
            ### If the container is not in the "running" state, usage will not be reported. 
            memory_total_mb = "N/A"
        outdict = {
            "cpu_total":cpu_percent,
            "memory_total_mb":memory_total_mb
                }
        return outdict 

    def get_status(self):
        """Get the current status of the container. This should be gotten by running the client.api.inspect method. 

        :return: A dictionary of custom status entries. 
        """
        custom_status = {}
        inspection = client.api.inspect_container(self.container.name)
        ## Possible statuses.
        docker_stats = {
                "created":"created",
                "restarting":"restarting",
                "running":"running",
                "paused":"paused",
                "exited":"exited",
                "dead":"dead"
                }
        state_dict = inspection["State"]
        status = state_dict["Status"]
        ## Parse further if exited: we want to say if we succeeded or failed. 
        error = state_dict["Error"] 
        if status == "exited":
            exitcode = state_dict["ExitCode"]
            if exitcode == 0: 
                status = "success"
            elif exitcode == 137: 
                status = "sigkill/oom"
            else:
                status = "failed"
        custom_status["status"] = status
        custom_status["error"] = error
        custom_status["starttime"] = state_dict["StartedAt"]
        if state_dict["FinishedAt"] == '0001-01-01T00:00:00Z':
            custom_status["finishtime"] = "N/A"
        else:    
            custom_status["finishtime"] = state_dict["FinishedAt"]
        return custom_status    

    def update_file(self):
        """Gets updates to status, usage, and stdout/err and aggregates them to be output together.   

        """
        writelines = self.get_stdout()
        writedict = {str(i):line for i,line in enumerate(writelines)}
        statusdict = self.get_status()
        usage = self.get_usage()
        self.rawfile["status"] = statusdict["status"]
        self.rawfile["reason"] = statusdict["error"]
        self.rawfile["cpu_usage"] = "{} %".format(usage["cpu_total"])
        self.rawfile["memory_usage"] = "{} MB".format(usage["memory_total_mb"])
        self.rawfile["job_start"] = statusdict["starttime"]
        self.rawfile["job_finish"] = statusdict["finishtime"]
        self.rawfile["std"] = writedict
        ## Remove keys from legacy usage to avoid confusion
        for key in ["stderr","stdout"]:
            try:
                del self.rawfile[key]
            except KeyError:
                pass

        
class NeuroCAASActivityLog(object):
    """Automatically generated log specifying information useful for NeuroCAAS to keep track of jobs as they run. Largely handled and read by automated services, not users or developers. 

    """
    ...
      


