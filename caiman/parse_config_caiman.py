## to parse the given configuration file: 
import sys
import os
import pickle
sys.path.append("/home/ubuntu/neurocaas_remote")
from ncap_utils.transfer_codebase.Interface_S3 import download
from ncap_utils.
from caiman.source_extraction.cnmf import params as params
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
    param_mode = configparams["param_mode"]
    ## If param_mode is advanced, import the caiman parameter dictionary uploaded by the user.  
    if param_mode == "advanced":
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
    ## If param_mode is simple, write the given parameters into a new caiman parameter dictionary. 
    elif param_mode == "simple":
        paramset = params.CNMFParams()
        try:
            other_params = configparams["params"]
            for key in other_params:
                paramset.change_params({key:other_params[key]})
            paramdict = paramset.to_dict()
            paramdict["online"]["path_to_model"] = "/home/ubuntu/caiman_data/model/cnn_model_online.h5"

        except Exception as e: 
            print("params not given")
            raise OSError("params not given correctly.")
    else:
        print("param mode {} not recognized. exiting.".format(param_mode))
        raise OSError("param dict not given correctly.")
        

    pickle.dump(paramdict,open(os.path.join(locname,"final_pickled_new"),"wb"))


    




