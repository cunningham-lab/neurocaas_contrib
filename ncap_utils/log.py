import boto3
import json
import os
import sys

## This is a script to update the job log corresponding to this dataset in aws s3. 
## Inputs: 
# We need the data name, without any external paths,x
# We need the path to the results directory. 

if __name__ == "__main__":
    bucketname = sys.argv[1]
    groupname = sys.argv[2]
    dataname = sys.argv[3]
    resultsdir = sys.argv[4]
    output = sys.argv[5]
    resultsdir_log = os.path.join(resultsdir,"logs")

    s3 = boto3.resource("s3")
    s3_client = boto3.client("s3")
    ssm_client = boto3.client("ssm","us-east-1")

    ## then the path to the file should be
    datastatus = "DATASET_NAME:{}_STATUS.txt".format(dataname)
    keypath = os.path.join(groupname,resultsdir_log,datastatus)

    ## Retrieve the file: 
    bucket = s3.Bucket(name = bucketname)
    objects = []
    for obj in bucket.objects.filter(Prefix = keypath):
        objects.append(obj)
        print(obj)
    assert len(objects) == 1, "there should only be one status, found {}".format(objects)

    ## Now get the text body: 
    Object = s3.Object(bucketname,objects[0].key)
    status_dict = json.loads(Object.get()["Body"].read())
    print(status_dict)

    ## Get the job status: 
    updated_command = ssm_client.list_commands(CommandId = status_dict["command"]) 
    status = updated_command["Commands"][0]["Status"]
    status_dict["status"] = status
    status_dict["reason"] = output
    
    ## Get the job output: 
    try:
        path = "/var/lib/amazon/ssm/{}/document/orchestration/{}/awsrunShellScript/0.awsrunShellScript/".format(status_dict["instance"],status_dict["command"])
        os.listdir(path)
        with open(os.path.join(path,"stdout")) as fout:
            stdout_content = fout.readlines()
            status_dict["stdout"] = stdout_content 
        with open(os.path.join(path,"stderr")) as ferr:
            stderr_content = ferr.readlines()
            status_dict["stderr"] = stderr_content


    except OSError as e: 
        print("path {} does not exist yet".format(path)) 
        raise OSError("other branch failed with error {}".format(e))
    
    statusobj = s3.Object(bucketname,keypath)
    statusobj.put(Body = (bytes(json.dumps(status_dict).encode("UTF-8"))))
    #s3_client.delete_object(Bucket=bucketname,Key = objects[0].key)
    
    
    ## stdout = 
    

    




