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
        stdout = {} 
        with open(os.path.join(neurocaasrootdir,"joboutput.txt")) as fout:
            for l,line in enumerate(fout):
                stdout[l] = line
            status_dict["stdout"] = stdout             

        stderr = {} 
        with open(os.path.join(neurocaasrootdir,"joberror.txt")) as ferr:
            for l,line in enumerate(ferr):
                stderr[l] = line
            status_dict["stderr"] = stderr            

    except OSError as e: 
        print("log data does not exist yet") 
        print(e)
        status_dict["stdout"] = "pending"
        status_dict["stderr"] = "pending"

    json.dump(status_dict,open(jsonpath,"w"),indent = 4)

