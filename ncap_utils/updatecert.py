## module to update the certificate.txt file
import boto3
from botocore.exceptions import ClientError
import traceback
import datetime
import json
import os
import sys
s3_resource = boto3.resource("s3")

def ls(bucket, path):
    """ Get all objects with bucket as strings"""
    return [
    objname.key.encode("utf-8") for objname in bucket.objects.filter(Prefix=path)
    ]

def load_json(bucket_name, key):
    """ """
    try:
        file_object = s3_resource.Object(bucket_name, key)
        raw_content = file_object.get()['Body'].read().decode('utf-8')
        dict_content = json.loads(raw_content)
    except ValueError as ve:
        print("Error loading config file. Error is: {}".format(ve))
        raise ValueError
    except ClientError as ce:
        e = ce.response["Error"]["Code"]
        print("Encountered AWS Error: {}".format(e))
        raise ValueError
        
    return dict_content

def load_cert(bucket_name, key):
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
        
    return raw_content

def find_linebreaks(arg):
    """
    Finds part of the file indicating the per-dataset log. 
    args: 
    arg (str): string to be compared to find linebreaks. 
    """
    temp = "================"
    return arg[0] == temp

if __name__ == "__main__":
    try:
        bucketname = sys.argv[1]
        resultspath = sys.argv[2]
        bucket = s3_resource.Bucket(bucketname)
        certpath = os.path.join(resultspath,"certificate.txt")
        writeobj = s3_resource.Object(bucketname,certpath)
        ## Load in the certificate:
        c = load_cert(bucketname,certpath)
        ## Make it easier to work with:
        clist = c.split("\n")
        indclist = [(cel,ci) for ci,cel in enumerate(clist)]
        
        ## Get out the location in the file we should write into
        linebreak_locs = filter(find_linebreaks,indclist)
        assert len(linebreak_locs) == 2, "should be start and end."
    except:
        e = traceback.format_exc()
        raise Exception("error getting certificate, not formatted for per-job logging. Message: {}".format(e))
    try:
        statusfiles = ls(bucket,os.path.join(resultspath,"DATASET_NAME"))
    except:
        e = traceback.format_exc()
        raise Exception("error getting status files. Message: {}".format(e))
        raise Exception("error getting status files.")
    

    dataset_template = "DATANAME: {n} | STATUS: {s} | TIME: {t} | LAST COMMAND: {r} | CPU_USAGE: {u}"
    dataset_template_init = "DATANAME: {n} | STATUS: {s} | TIME: {t} | LAST COMMAND: {r}"
    for e,i in enumerate(range(linebreak_locs[0][1]+1,linebreak_locs[1][1])):
        try:
            ## Get the files that we would like to update with:
            rawstatus = load_json(bucketname,statusfiles[e])
            try:
                cpu = rawstatus["cpu_usage"][0].encode("utf-8")
                message = dataset_template.format(n = rawstatus["input"],s = rawstatus["status"],t = str(datetime.datetime.now()), r = rawstatus["reason"][0].encode("utf-8"), u = cpu)
            except KeyError:
                message = dataset_template_init.format(n = rawstatus["input"],s = rawstatus["status"],t = str(datetime.datetime.now()), r = rawstatus["reason"][0].encode("utf-8"))

            ## Get template for what update should look like:  
        except: 
            e = traceback.format_exc()
            print(e)
            message = "[Logging Error], analysis is proceeding."
        clist[i] = message

    ## Now write the new log: 
    writeobj.put(Body = "\n".join(clist).encode("utf-8"))


        
    
    # Now add in dataset  
    #content = clist[content_range]
    ## 
    #names = []
    #statuses = []
    #for sfile in statusfiles:
    #    statusfile = load_cert(bucketname,sfile) 
    #    statusdict = json.loads(statusfile.decode("utf-8"))
    #    statuses.append(statusdict["status"])
    #    names.append(statusdict["input"])
    #print(c+("\nDATASETS TO ANALYZE: \n ============== \n {d1}: STATUS: {s1} \n {d2}: STATUS: {s2}\n ==============".format(d1 = names[0],s1 = statuses[0],d2 = names[1], s2 = statuses[1])))
    #print(statusdict)


