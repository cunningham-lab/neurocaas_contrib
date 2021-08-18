# Script to run pca given a dataset and numpy array. 
from sklearn.decomposition import PCA
import numpy as np
import sys
import pickle
import yaml
import os

loc = os.path.abspath(os.path.dirname(__file__))
"""Usage 
python pca.py datapath configpath resultpath

Runs PCA via scikit learn on a given numpy file (.npy), saved via numpy.save. Requires a configuration file specifying the parameters to apply to data. 
Saves out an sklearn.decomposition.PCA object that has been fit to a directory, resultpath.

:param datapath: path to a numpy array of shape (samples,features) respecting sklearn format. 
:param configpath: path to a config file that has the field "n_components", specifying the number of components we want to fit in our model.  
:param resultpath: path to a directory where we will write a file, pcaresults
"""


if __name__ == "__main__": 
    print("--Getting Arguments--")
    datapath = sys.argv[1]
    configpath = sys.argv[2]
    resultpath = sys.argv[3]
    print("--Data: {} Config: {} Results: {}--".format(datapath,configpath,resultpath))
    dataarray = np.load(datapath) ## assume data is in form (samples,features)
    with open(configpath,"r") as f:
        config = yaml.safe_load(f)
    print("--Data and Config Loaded into memory--")
    pca = PCA(config["n_components"])    
    pca.fit(dataarray)
    print("--Model on data, performing PCA fit with {} components. Saving to file--".format(config["n_components"]))
    with open(os.path.join(resultpath,"pcaresults"),"wb") as f:
        pickle.dump(pca,f)



     



