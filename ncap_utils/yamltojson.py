import sys
import os
import yaml
import json

## This is a python module that parses a configuration file, and does nothing if it is a json file, and returns a json if it is a yaml file.
if __name__ == "__main__":
    dict_path = sys.argv[1]
    dicttype = None
    if dict_path.endswith("json"):
        dicttype = "json"
    elif dict_path.endswith("yaml"):
        dicttype = "yaml"
    else:
        pass
    assert dicttype is not None

    if dicttype == "json":
       jsonpath = dict_path 
    else:
        ## First import the dictionary
        with open(dict_path,"r") as yfile:
            ydict = yaml.safe_load(yfile)
        jsonpath = dict_path.replace(".yaml",".json")
        with open(jsonpath,"w") as jfile:
            json.dump(ydict,jfile)
    print(os.path.basename(jsonpath))

       
