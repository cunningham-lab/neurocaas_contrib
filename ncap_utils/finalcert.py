## module to finalize the certificate.txt file
import boto3
from botocore.exceptions import ClientError
import traceback
import datetime
import json
import os
import sys
from updatecert import ls, load_json, load_cert, find_linebreaks, s3_resource
s3_resource = boto3.resource("s3")

def find_datapath(arg,datapath):
    """
    Find places where the log provides the datapath provided as a curried function: 
    """
    findthis = "DATANAME: {} |".format(datapath)
    return "DATANAME: {} |".format(datapath) in arg[0]

if __name__ == "__main__":
    try:
        bucketname = sys.argv[1]
        resultspath = sys.argv[2]
        ## We additionally need to match on the name of the dataset:
        datapath = sys.argv[3]
        finalcode = sys.argv[4]
        bucket = s3_resource.Bucket(bucketname)
        certpath = os.path.join(resultspath,"certificate.txt")
        writeobj = s3_resource.Object(bucketname,certpath)
        ## Load in the certificate:
        c = load_cert(bucketname,certpath)
        ## Make it easier to work with:
        clist = c.split("\n")
        indclist = [(cel,ci) for ci,cel in enumerate(clist)]
        
        ## Get out the location in the file we should write into
        datafunc = lambda x: find_datapath(x,datapath)
        data_loc = filter(datafunc,indclist)
        assert len(data_loc) == 1, " should be only one location."
    except:
        e = traceback.format_exc()
        raise Exception("error getting certificate, not formatted for per-job logging. Message: {}".format(e))
    
    dataset_template = "DATANAME: {n} | STATUS: {s} | TIME: {t} (finished)"
    try:
        message = dataset_template.format(n = datapath, s = finalcode, t = str(datetime.datetime.now()))
        clist[data_loc[0][1]] = message
    except:
        raise Exception("error writing message, not formatted for per-job logging. Message: {}".format(e))


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


