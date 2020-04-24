## to parse the given configuration file: 
import sys
import os
import pickle
from ncap_utils.transfer_codebase.Interface_S3 import download
import json

## Inputs: 
## bucket 
## configuration file name
## location name. 
if __name__ == "__main__":
    
    bucketname = sys.argv[1]
    configname = sys.argv[2]
    locname = sys.argv[3]

    configparams = json.load(open(configname,'r'))
    try:
        paramdict = configparams["param_dict"]
        paramdict_name = os.path.basename(paramdict)
        download(bucketname,paramdict,locname+"/")
        path_paramdict = os.path.join(locname,paramdict_name)
        paramdict = pickle.load(open(path_paramdict,"rb"))
    except Exception as e:
        #print("param_dict param does not exist, with error: {}".format(e))
        raise OSError("no param dict!")
    try:
        cnn = configparams["cnn"]
        download(bucketname,cnn,locname+"/")
        path_cnn = os.path.join(locname,os.path.basename(path_paramdict))
        paramdict["online"]["path_to_model"] = path_cnn 
        print(paramdict)

    except Exception as e:
        print("cnn param does not exist!, error: {}".format(e))
        paramdict["online"]["path_to_model"] = "/home/ubuntu/caiman_data/model/cnn_model_online.h5"

    pickle.dump(paramdict,open(os.path.join(locname,"final_pickled"),"wb"))


    




