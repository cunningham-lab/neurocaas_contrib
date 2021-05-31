## Suite of tools for developers to monitor community usage of their analyses.
## Includes: 
# Cost monitoring
# Active jobs
# Job history
import numpy as np
import logging
import boto3
import localstack_client.session
from botocore.exceptions import ClientError,NoRegionError
import json
from datetime import timedelta
import time
from datetime import datetime as datetime
import os
from .log import NeuroCAASCertificate,NeuroCAASDataStatusLegacy

s3_client = boto3.client("s3")
s3_resource = boto3.resource("s3")

try:
    cfn_client = boto3.client("cloudformation")
    logs_client = boto3.client("logs")
except NoRegionError: ## Handle ReadTheDocs Build.    
    cfn_client = boto3.client("cloudformation",region_name = os.environ["REGION"])
    logs_client = boto3.client("logs",region_name = os.environ["REGION"])


jobprefix = "job__{s}_{t}" # parametrized by stackname, timestamp. 

class RangeFinder():
    """object class to keep track of the range of dates we are considering. 

    """
    def __init__(self):
        self.form = "%Y-%m-%dT%H:%M:%SZ"
        self.baseline = datetime.now()
        ## Keep track of interval by calculating biggest and smallest differences to right now.  
        self.diff_min = np.inf
        self.diff_max = -np.inf
        self.starttime = None
        self.endtime = None

    def diff(self,datetime_str):   
        """Takes in a string formatted datetime (formatted as self.form), and compares it with now. 

        """
        timeform = datetime.strptime(datetime_str,self.form)
        diff = self.baseline-timeform
        diff_secs = diff.total_seconds()
        logging.info(diff_secs)
        return diff_secs

    def update(self,datetime_str):
        """Takes in a string formatted datetime, and updates the start and end dates if necessary.

        """
        if datetime_str is not None:
            diff = self.diff(datetime_str)
            logging.info("{}, {}, {}".format(diff,self.diff_max,self.diff_min))
            if diff > self.diff_max: 
                self.starttime = datetime_str
                self.diff_max = diff
            if diff < self.diff_min:   
                self.endtime = datetime_str
                self.diff_min = diff
    def return_range(self):    
        print("Started at {}, ended at {}".format(self.starttime,self.endtime))
    
    def range_months(self):
        startdate = datetime.strptime(self.starttime,self.form)
        enddate = datetime.strptime(self.endtime,self.form)
        startmonth = "{}/{}".format(startdate.month,startdate.year)
        endmonth = "{}/{}".format(enddate.month,enddate.year)
        return startmonth,endmonth

## Cost monitoring

def ls_name(bucket_name, path):
    """ Get the names of all objects in bucket under a given prefix path as strings. Takes the name of the bucket as input, not hte bucket itself for usage outside of the utils module.  
    
    :param bucket_name: name of s3 bucket to list. 
    :type bucket_name: str
    :param path: prefix path specifying the location you want to list. 
    :type path: str
    :return: A list of strings describing the objects under the specified path in the bucket. 
    :rtype: list of strings
    """
    bucket = s3_resource.Bucket(bucket_name)
    return [
        objname.key for objname in bucket.objects.filter(Prefix=path)
    ]

def load_json(bucket_name, key):
    """ Function to load the contents of a json file stored in S3 into memory for a lambda function. 

    :param bucket_name: the name of the bucket where the json file lives. 
    :type bucket_name: str
    :param key: the path to the json object. 
    :type key: str
    :raises: ValueError. If the key does not point to a properly formatted json file, an exception will be raised. 
    :return: json content: the content of the json file. 
    :rtype: dict
    """
    try:
        file_object = s3_resource.Object(bucket_name, key)
    except ClientError as e:
        raise ClientError("S3 resource object declaration (and first aws api call) failed.")
    try:
        raw_content = file_object.get()['Body'].read().decode('utf-8')
        json_content = json.loads(raw_content)
    except ValueError as ve:
        raise ValueError("[JOB TERMINATE REASON] Could not load config file. From parser: {}".format(ve))

    ## Transfer type 
    return json_content 

def get_analysis_cost(path,bucket_name):
    """ Given a username and the name of a bucket to look in, gets the cost incurred so far by a given group (as recorded in logs)  

    """
    group_name = path
    assert len(group_name) > 0; "[JOB TERMINATE REASON] Can't locate the group that triggered analysis, making it impossible to determine incurred cost."
    logfolder_path = "logs/{}/".format(group_name)
    full_reportpath = os.path.join(logfolder_path,"i-")
    ## now get all of the computereport filenames:
    all_files = ls_name(bucket_name,full_reportpath)

    ## for each, we extract the contents:
    jobdata = {}
    cost = 0
    ## now calculate the cost:
    for jobfile in all_files:
        instanceid = jobfile.split(full_reportpath)[1].split(".json")[0]
        jobdata = load_json(bucket_name,jobfile)
        price = jobdata["price"]
        start = jobdata["start"]
        end = jobdata["end"]
        try:
            starttime = datetime.strptime(start, "%Y-%m-%dT%H:%M:%SZ")
            endtime = datetime.strptime(end, "%Y-%m-%dT%H:%M:%SZ")
            diff = endtime-starttime
            duration = abs(diff.seconds)
            instcost = price*duration/3600.
        except TypeError:
            ## In rare cases it seems one or the other of these things don't actually have entries. This is a problem. for now, charge for the hour:
            instcost = price
        cost+= instcost

    return cost
    
## Job history (imported from neurocaas/ncap_iac/ncap_blueprints/dev_utils/track_usage.py)
form = "%Y-%m-%dT%H:%M:%SZ"

### Module with tools to track usage for each individual stack.
def check_bucket_exists(bucket):
    if s3_resource.Bucket(bucket).creation_date is None:
        assert 0, "bucket {} does not exist".format(bucket)
    else:
        pass

def get_users(dict_files):
    """
    Presented with a dict of files (response of list_objects_v2), gets usernames from them. Asserts that buckets must be correctly formatted for logging (have an active and logs subfolder.) 
    """

    users = [os.path.basename(li["Key"][:-1]) for li in dict_files["Contents"] if li["Key"].endswith("/")]
    try:
        users.remove("active")
    except ValueError:
        print("bucket not correctly formatted. skipping. ")
        users = []

    try:
        users.remove("logs")
    except ValueError:
        print("bucket not correctly formatted. skipping. ")
        users = []

    return users

def get_jobs(dict_files):
    """Given the raw response output, returns a flat list of all the jobs that have been run. 

    :param dict_files: raw output of list objects api. 
    """
    activity = [li["Key"] for li in dict_files["Contents"] if li["Key"].endswith(".json")]
    return activity

def sort_activity_by_users(dict_files,userlist):
    """
    When given the raw response output + list of usernames, returns a dictionary of files organized by that username. Passes on debugging logs and logs that are currently active. 
    :param dict_files: raw output of list objects api. 
    :param userlist: a list of usernames for whom we will assign jobs. 
    :return: userdict, a dictionary indexed by user names, with values giving lists of jobs attributed to that user.
    """
    activity = [li["Key"] for li in dict_files["Contents"] if li["Key"].endswith(".json")]
    userdict = {name:[] for name in userlist}
    for a in activity:
        user = os.path.basename(os.path.dirname(a))
        try:
            userdict[user].append(a)
        except KeyError as e:
            if user in ['active','debug']:
                pass
            else:
                userdict[user] = []
                userdict[user].append(a)
    return userdict

def get_user_logs(bucket_name):
    """
    returns a list of s3 paths corresponding to logged users inside a bucket.

    :param bucket_name: the name of the s3 bucket we are looking for
    """

    try:
        print(bucket_name)
        l = s3_client.list_objects_v2(Bucket=bucket_name,Prefix = "logs")
    except ClientError as e:
        print(e.response["Error"])
        raise
    checktruncated = l["IsTruncated"]
    if checktruncated:
        print("WARNING: not listing all results.")
    else:
        print("Listing all results.")

    ## Get Users
    users = get_users(l)
    users_dict = sort_activity_by_users(l,users)
    return users_dict

def get_duration(start,end):
    """
    Get the duration of a job from a pair of strings using datetime.
    2020-05-17T01:21:05Z
    """
    starttime = datetime.strptime(start,form)
    endtime = datetime.strptime(end,form)
    diff = endtime-starttime
    diff_secs = diff.total_seconds()
    return diff_secs

def get_month(start):
    time = datetime.strptime(start,form)
    return time.month


def calculate_usage(bucket_name,usage_list,user):
    """
    gets the json files containing the usage for a particular user, and returns the total (number of hours, cost, and number of jobs run) per month.
    :param bucket_name: string giving the s3 bucket we are reading into.
    :param usage_list: a list of job logs, for a particular user authorized to use this analysis. 
    :param user: the user to whom we should assign this usage. 
    """

    months = ["January","February","March","April","May","June","July","August","September","October","November","December"]
    monthly_cost = {months[i]:0 for i in range(12)}
    monthly_time = {months[i]:0 for i in range(12)}
    usage_compiled = {"username":user,"cost":monthly_cost,"duration":monthly_time}

    for job in usage_list:
        usage_dict = load_json(bucket_name,job)
        if None in [usage_dict["start"],usage_dict["end"]]:
            continue
        duration = get_duration(usage_dict["start"],usage_dict["end"])
        month = get_month(usage_dict["start"])
        cost = (usage_dict["price"]/3600)*duration
        usage_compiled["cost"][months[month]] += cost
        usage_compiled["duration"][months[month]] += duration

    return usage_compiled

def calculate_parallelism(bucket_name,usage_list,user):
    """calculates the paralellism of user's usage. How much of the total running job time was spent on jobs running together? 

    """
    by_job = {}
    job_rfs = {}
    for inst in usage_list:
        rf_start = RangeFinder()
        rf_end = RangeFinder()
        usage_dict = load_json(bucket_name,inst)
        if all([usage_dict[state] is None for state in ["start","end"]]):
            logging.warning("skipping something for user {}".format(user))
            print("skipping something for user {}".format(user))
            continue

        job = usage_dict["jobpath"]
        try:
            job_rfs[job]["rf_start"].update(usage_dict["start"])
            job_rfs[job]["rf_end"].update(usage_dict["end"])
            by_job[job]["instances"].append(usage_dict)
            try:
                by_job[job]["durations"][usage_dict["instance-id"]] = get_duration(usage_dict["start"],usage_dict["end"])
            except TypeError:    
                by_job[job]["durations"][usage_dict["instance-id"]] = None
            by_job[job]["laststart"] = job_rfs[job]["rf_start"].endtime
            by_job[job]["firstend"] = job_rfs[job]["rf_end"].starttime

        except KeyError:    
            job_rfs[job] = {"rf_start":RangeFinder(),"rf_end":RangeFinder()}
            job_rfs[job]["rf_start"].update(usage_dict["start"])
            job_rfs[job]["rf_end"].update(usage_dict["end"])
            by_job[job] = {"instances":[usage_dict]}
            #####by_job[job]["instances"] = [usage_dict]
            try:
                by_job[job]["durations"] = {usage_dict["instance-id"]:get_duration(usage_dict["start"],usage_dict["end"])}
            except TypeError:    
                by_job[job]["durations"] = {usage_dict["instance-id"]:None}
            by_job[job]["laststart"] = job_rfs[job]["rf_start"].endtime
            by_job[job]["firstend"] = job_rfs[job]["rf_end"].starttime

    return by_job

def postprocess_jobdict(by_job):
    """Given a dictionary where the keys are job names, and the values are dictionaries with metadata about that job, looks in particular for jobs where some of the time entries have been neglected. If just the Start time has been neglected, replaces that with the last recorded start time as an esimate, and fills in the corresponding duration. If the whole job has no start or end times, remove it.     
    """
    ### postprocessing: if starts and ends are all none, remove job.         
    to_del = []
    for jobname,jobdict in by_job.items():
        if jobdict["laststart"] is None or jobdict["firstend"] is None:
            to_del.append(jobname)
            continue ## gonna delete this one
        for i in jobdict["instances"]:
            if i["end"] is None:
                to_del.append(jobname)
                continue ## gonna delete this one
            if i["start"] is None:
                i["start"] = jobdict["laststart"]
                by_job[jobname]["durations"][i["instance-id"]] = get_duration(i["start"],i["end"])

    [by_job.pop(td) for td in set(to_del)]        
    return by_job

def calculate_parallelism_nones(bucket_name,usage_list,user):
    """ Organizes individual runs into jobs, enven if none. 

    """
    by_job = {}
    job_rfs = {}
    for inst in usage_list:
        rf_start = RangeFinder()
        rf_end = RangeFinder()
        usage_dict = load_json(bucket_name,inst)
        if all([usage_dict[state] is None for state in ["start","end"]]):
            pass

        job = usage_dict["jobpath"]
        try:
            job_rfs[job]["rf_start"].update(usage_dict["start"])
            job_rfs[job]["rf_end"].update(usage_dict["end"])
            by_job[job]["instances"].append(usage_dict)
            try:
                by_job[job]["durations"][usage_dict["instance-id"]] = get_duration(usage_dict["start"],usage_dict["end"])
            except TypeError:    
                by_job[job]["durations"][usage_dict["instance-id"]] = None
            by_job[job]["laststart"] = job_rfs[job]["rf_start"].endtime
            by_job[job]["firstend"] = job_rfs[job]["rf_end"].starttime

        except KeyError:    
            job_rfs[job] = {"rf_start":RangeFinder(),"rf_end":RangeFinder()}
            job_rfs[job]["rf_start"].update(usage_dict["start"])
            job_rfs[job]["rf_end"].update(usage_dict["end"])
            by_job[job] = {"instances":[usage_dict]}
            #####by_job[job]["instances"] = [usage_dict]
            try:
                by_job[job]["durations"] = {usage_dict["instance-id"]:get_duration(usage_dict["start"],usage_dict["end"])}
            except TypeError:    
                by_job[job]["durations"] = {usage_dict["instance-id"]:None}
            by_job[job]["laststart"] = job_rfs[job]["rf_start"].endtime
            by_job[job]["firstend"] = job_rfs[job]["rf_end"].starttime

    return by_job

class LambdaMonitor():
    """Base class for lambda monitoring. Has specific subtypes for main and sub lambdas

    """
    def __init__(self,stackname):
        """
        """
        self.stackname = stackname
        self.lambda_pid = self.get_lambda_id()
        self.log_group = "/aws/lambda/{}".format(self.lambda_pid)

    def get_logs(self,hours = 1):
        """Get the lambda logs indicating NeuroCAAS job processing for the last {hours} hours. 
        The result will be returned as a list of dictionaries, with the key indicating the request id, and the value the lines of text included. 
        Code from :https://stackoverflow.com/questions/59240107/how-to-query-cloudwatch-logs-using-boto3-in-python
        :param hours: the number of hours to start collecting logs in.  
        :returns: a list of dictionaries, containing logs for requests in reverse chronological order. 
        """
        start_query_response = logs_client.start_query(
                logGroupName = self.log_group,
                startTime = int((datetime.today()-timedelta(hours=hours)).timestamp()),
                endTime = int(datetime.today().timestamp()),
                queryString = "fields @logStream, @timestamp, @message" ## these are the fields we will want to parse. 
                )
        query_id = start_query_response["queryId"]
        response = None
        while response == None or response["status"] == "Running":
            time.sleep(1)
            response = logs_client.get_query_results(
                    queryId= query_id
                    )
        parsed = self.parse_response(response)    
        return parsed
           
    def parse_response(self,response):    
        """Lambda logs are given as lists of requests in reverse chronological order, one per line. Let's find t 

        :param response: the output of boto3.client("logs").get_query_results()
        :returns: queries grouped by logstream 
        """
        all_results = response["results"]
        ## ordered unique implementation from https://stackoverflow.com/questions/480214/how-do-you-remove-duplicates-from-a-list-whilst-preserving-order
        def f7(seq):
            seen = set()
            seen_add = seen.add
            return [x for x in seq if not (x in seen or seen_add(x))]

        logstreams = f7([li[0]["value"] for li in all_results])
        streamdict = {s:[] for s in logstreams}
        ## Now write the log messages into the streams, 
        [streamdict[li[0]["value"]].append([li[-2]["value"]]) for li in all_results]
        [streamdict[s].reverse() for s in streamdict.keys()]
        ## Write into an ordered list of dictionaries. 
        ordered = [{s:" ".join(sdi[0] for sdi in streamdict[s])} for s in logstreams]
        return ordered
        
    def print_log(self,index = 0,hours = 1):    
        """Print the contents of a log. By default, prints the most recent log (index = 0). 

        :param index: the index of the log to print. By default, it's 0 (latest) 
        :param hours: the number of hours to start collecting logs in.  
        """
        parsed = self.get_logs(hours = hours)
        try:
            selected = parsed[index]
        except IndexError:    
            raise IndexError("There are {} logs in this time range- log {} does not exist".format(len(parsed),index))
        print("logstream: "+list(selected.keys())[0])
        print("message: \n"+list(selected.values())[0])

class LogMonitor(LambdaMonitor):
    """Monitor the logs coming off of a given analysis. 

    """
    def get_lambda_id(self):    
        """Code to get the physical resource id of a cfn main lambda function from the stackname: 

        :returns: physical resource id of the cloudformation lambda function.     
        """
        prid = cfn_client.describe_stack_resources(StackName=self.stackname,LogicalResourceId="FigLambda")["StackResources"][0]["PhysicalResourceId"]
        return prid

class JobMonitor(LambdaMonitor):
    """Monitor a job as it is running. Given a submit file as input, uses it to trace details about a running job. 

    """

    def get_lambda_id(self):    
        """Code to get the physical resource id of a cfn main lambda function from the stackname: 

        :returns: physical resource id of the cloudformation lambda function.     
        """
        prid = cfn_client.describe_stack_resources(StackName=self.stackname,LogicalResourceId="MainLambda")["StackResources"][0]["PhysicalResourceId"]
        return prid


    def register_submit(self,submitfile):    
        """ Use submit file info to process further. 

        """
        with open(submitfile,"r") as f:
            data = json.load(f)
        assert data.get("dataname",False), "name of the dataset must be provided"    
        assert data.get("configname",False), "name of the config file must be provided"    
        assert data.get("timestamp",False), "timestamp must be provided."    
        return data

    def get_certificate(self,submitfile):    
        """Get the certificate file corresponding to a given submit file. 

        :param submitfile: path to a submit file. 
        :returns: a NeuroCAASCertificate object. 
        """
        submitdict = self.register_submit(submitfile)

        if type(submitdict["dataname"]) == str:
            groupname = submitdict["dataname"].split("/",1)[0]
        elif type(submitdict["dataname"]) == list:
            groupname = submitdict["dataname"][0].split("/",1)[0]

        foldername = jobprefix.format(s=self.stackname,t=submitdict["timestamp"])
        fullpath = os.path.join("s3://",self.stackname,groupname,"results",foldername,"logs","certificate.txt")
        ### TODO: wont load if the certificate did not reach processing stage yet. Throws assertion error 
        cert = NeuroCAASCertificate(fullpath)
        return cert

    def get_datasets(self,submitfile):    
        """Get the list of datasets associated with a given submit file. 

        """
        cert = self.get_certificate(submitfile)
        instance_cert = cert.get_instances()
        return instance_cert

    def get_datastatus(self,submitfile,dataset):    
        """Get the datastatus file associated with a given submit file and dataset. 

        """
        submitdict = self.register_submit(submitfile)

        groupname = submitdict["dataname"].split("/",1)[0]

        foldername = jobprefix.format(s=self.stackname,t=submitdict["timestamp"])
        fullpath = os.path.join("s3://",self.stackname,groupname,"results",foldername,"logs","DATASET_NAME:{}_STATUS.txt".format(dataset))
        status = NeuroCAASDataStatusLegacy(fullpath)
        return status
        

        


        





