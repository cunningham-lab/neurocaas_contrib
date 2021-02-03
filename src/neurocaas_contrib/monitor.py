## Suite of tools for developers to monitor community usage of their analyses.
## Includes: 
# Cost monitoring
# Active jobs
# Job history
import boto3
import json
from datetime import datetime as datetime
import os

s3_client = boto3.client("s3")
s3_resource = boto3.resource("s3")

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
    s3 = boto3.resource('s3')
    if s3.Bucket(bucket).creation_date is None:
        assert 0, "bucket {} does not exist".format(bucket)
    else:
        pass

def get_users(dict_files):
    """
    Presented with a dict of files (response of list_objects_v2), gets usernames from them.
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



def sort_activity_by_users(dict_files,userlist):
    """
    When given the raw resposne output + list of usernames, returns a dictionary of files organized by that username.
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

    s3_client = boto3.client("s3")
    try:

        l = s3_client.list_objects_v2(Bucket=bucket_name,Prefix = "logs")
    except ClientError as e:
        print(e.response["Error"])
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






