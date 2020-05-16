## Newest python script as of 11/14
import time
import os
import sys
from collections import deque
import json 


if __name__ == "__main__":
    jsonpath = sys.argv[1]
    neurocaasrootdir = sys.argv[2]
    status_dict = json.load(open(jsonpath,"r"))
    ## Now get the corresponding stdout and stderr logs: 
    try:
        path = "/var/lib/amazon/ssm/{}/document/orchestration/{}/awsrunShellScript/0.awsrunShellScript/".format(status_dict["instance"],status_dict["command"])
        os.listdir(path)
        with open(os.path.join(path,"stdout")) as fout:
            stdout = deque(maxlen=20)
            for line in fout:
                stdout.append(line)
            status_dict["stdout"] = list(stdout) 
        stdout = []
        with open(os.path.join(neurocaasrootdir,"joboutput.txt")) as fout:
            for line in fout:
                stdout.append(line)
            status_dict["stdout"] = "".join(stdout)            

        with open(os.path.join(path,"stderr")) as ferr:
            stderr = deque(maxlen=20)
            for line in ferr:
                stderr.append(line)
            status_dict["stderr"] = list(stderr) 
        stderr = []
        with open(os.path.join(neurocaasrootdir,"joberror.txt")) as ferr:
            for line in ferr:
                stderr.append(line)
            status_dict["stderr"] = "\\n".join(stderr)            

    except OSError as e: 
        print("path {} does not exist yet".format(path)) 
        print(e)
        status_dict["stdout"] = "pending"
        status_dict["stderr"] = "pending"

    json.dump(status_dict,open(jsonpath,"w"))

