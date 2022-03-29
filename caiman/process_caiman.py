# -*- coding: utf-8 -*-
"""
Pipeline for NCAP batch processing. Adapted wholesale from figure generation scripts in CaImAn/use_cases/eLife_scripts/preprocessing_files.
"""
import cv2

try:
    cv2.setNumThreads(1)
except:
    print('Open CV is naturally single threaded')

try:
    if __IPYTHON__:
        print(1)
        # this is used for debugging purposes only. allows to reload classes
        # when changed
        get_ipython().magic('load_ext autoreload')
        get_ipython().magic('autoreload 2')
except NameError:
    print('Not launched under iPython')

import caiman as cm
import numpy as np
import os
import time
import pylab as pl
import scipy
import sys
from caiman.source_extraction.cnmf import cnmf as cnmf
from caiman.source_extraction.cnmf.estimates import Estimates, compare_components
from caiman.cluster import setup_cluster
from caiman.source_extraction.cnmf import params as params
from caiman.source_extraction.cnmf.cnmf import load_CNMF
from caiman.base.movies import from_zipfiles_to_movie_lists
import tarfile
import zipfile as zipfilemod
import shutil
import json
import pickle
import glob
import logging
import warnings

logging.basicConfig(format=
                    "%(relativeCreated)12d [%(filename)s:%(funcName)20s():%(lineno)s]"\
                    "[%(process)d] %(message)s",
                    level=logging.INFO)

warnings.filterwarnings("ignore", category=FutureWarning)

## Get parameters for processing from script input: 
param_dict = sys.argv[1]
zipfile = sys.argv[2]
output_loc = sys.argv[3]
## Get additional parameters from the config file passed: 
config_dict_path = sys.argv[4]
config_dict = json.load(open(config_dict_path,'r'))
## Should we fit, or fit and then refit?
fitting_mode = config_dict["fitting_mode"]
component_eval = config_dict["component_eval"]

reload = False
plot_on = False

save_all = False
check_result_consistency = False

print_figs = False
skip_refinement = False
backend_patch = 'local'
backend_refine = 'local'
n_processes = 64
base_folder = '/home/ubuntu/ncapdata'
n_pixels_per_process = 4000
block_size = 5000
num_blocks_per_run = 20

## Sanitize params. 
#assert len(zipfile.split(".zip")) == 2, "{} is not properly named zip file.".format(zipfile)
assert any([zipfile.endswith(ext) for ext in [".zip",".tar.gz"]]), "{} is not a correctly formatted zip file".format(zipfile)

data_dirname = os.path.dirname(zipfile)

if zipfile.endswith(".zip"):
    ### Now give the path to the file we want to analyze, convert to movie names
    mov_names = from_zipfiles_to_movie_lists(zipfile)
 
    ## Now give the name that this movie should have.  
    data_noext = os.path.basename(zipfile).split(".zip")[0]
## if ".tar.gz", convert: 
elif zipfile.endswith(".tar.gz"):
    data_noext = os.path.splitext(os.path.basename(zipfile))[0]
    with tarfile.open(name = zipfile,mode = "r|gz") as tarf:
        tarf.extractall(data_dirname)
    ## what is the directory where this data is stored? 
    with tarfile.open(name = zipfile,mode = "r|gz") as tarf:
        tif_dirname = tarf.next().name
        
    file_names = [os.path.join(data_dirname,tif_dirname,f) for f in os.listdir(os.path.join(data_dirname,tif_dirname))]    
    file_names.sort()
    nb_files = len(file_names)
    length_file = 100
    m = cm.load_movie_chain(file_names)
    mov_names = []
    for t in np.arange(0,nb_files,length_file):
        movie_name = os.path.join(data_dirname,data_noext+"fullmovie{}.tif".format(t))        
        m[t:t+length_file].save(movie_name)
        mov_names.append(movie_name)
    



## TODO sanitize dictionary. 

## Get the parameter dictionary from inputs: 
parameter_dict = pickle.load(open(param_dict,'rb')) 
## Initialize an empty parameter dictionary:  
opts = params.CNMFParams()
for key in parameter_dict.keys():
    opts.change_params(parameter_dict[key])

## Terminate previous jobs for safety: 
#try:
#    cm.stop_server()
#    dview.terminate()
#except:
#    print("No clusters to stop")
#
### Start new cluster jobs: 
#c,dview,_ = setup_cluster(
#        backend=backend_patch,n_processes=8,single_thread = False)



## Write this movie and rename:  
#fname_zip = cm.save_memmap(mov_names,dview=dview,order="C",add_to_movie=0)
#data_moviename = fname_zip
#print(fname_zip,data_moviename,"move from here to there")
#shutil.move(fname_zip,data_moviename)
# Now add as a parameter: 
opts.change_params({'fnames':mov_names})
opts.change_params({'only_init':False})

try:
    cm.stop_server()
    dview.terminate()
except:
    print("No clusters to stop")

## Now we will begin actual processing: 
c,dview,n_processes = setup_cluster(
        backend=backend_patch,n_processes=n_processes,single_thread=False)


#Yr,dims,T = cm.load_memmap(data_moviename)
#d1,d2 = dims
#images = np.reshape(Yr.T,[T]+list(dims),order="F")

#Y = np.reshape(Yr,dims+(T,),order = "F")
#m_images = cm.movie(images)

#check_nan = False

## Extract spatial+temporal components:
t1 = time.time()
print("Starting CNMF")
cnm = cnmf.CNMF(n_processes,params = opts,dview=dview)
print(opts,"options")
cnm = cnm.fit_file(motion_correct = True)

if fitting_mode == "fit":
    print("fitting once. ")
    if component_eval == True: 
        print("evaluating components")
        Yr,dims,T = cm.load_memmap(cnm.mmap_file)
        d1,d2 = dims

        images = np.reshape(Yr.T,[T]+list(dims),order="F")
        cnm.estimates.evaluate_components(images,cnm.params,dview=dview)
        cnm.estimates.select_components(use_object=True)
    else:
        print("not evaluating components")

    data_moviepath = os.path.join(output_loc,data_noext)

    ## saving this first bc model save fails. 
    np.savez(data_moviepath+"C.npz",cnm.estimates.C)
    np.savez(data_moviepath+"R.npz",cnm.estimates.R)
    np.savez(data_moviepath+"A.npz",cnm.estimates.A)

    try:
        cnm.save(data_moviepath+'_cnmf_obj.hdf5')
    except ValueError as e:    
        print("Ran into error while saving:")
        print(e)

elif fitting_mode == "refit":
    print("refitting, initialized from initial fit.")
    Yr,dims,T = cm.load_memmap(cnm.mmap_file)
    d1,d2 = dims
    images = np.reshape(Yr.T,[T]+list(dims),order="F")
    
    t_patch = time.time() - t1
    try:
        dview.terminate()
    except:
        pass
    
    c, dview,n_processes = cm.cluster.setup_cluster(
            backend=backend_refine,n_processes=n_processes,single_thread=False)
    
    ## Update some parameters
    cnm.params.change_params({'update_background_components':True,'skip_refinement':False,'n_pixels_per_process':n_pixels_per_process,'dview':dview})
    
    ## Refine:
    t1 = time.time()
    cnm2 = cnm.refit(images,dview=dview)
    if component_eval == True: 
        print("evaluating components")
        cnm2.estimates.evaluate_components(images,cnm2.params,dview=dview)
        cnm2.estimates.select_components(use_object=True)
    else:
        print("not evaluating components")

    data_moviepath = os.path.join(output_loc,data_noext)

    try:
        cnm2.save(data_moviepath+'_cnmf_obj.hdf5')
    except ValueError as e:    
        print("Ran into error while saving:")
        print(e)

    np.savez(data_moviepath+"A.npz",cnm2.estimates.A)
    np.savez(data_moviepath+"C.npz",cnm2.estimates.C)
    np.savez(data_moviepath+"R.npz",cnm2.estimates.R)
else:
    print("not a valid option, returning standard fit.")
    if component_eval == True: 
        print("evaluating components")
        Yr,dims,T = cm.load_memmap(cnm.mmap_file)
        d1,d2 = dims

        images = np.reshape(Yr.T,[T]+list(dims),order="F")
        cnm.estimates.evaluate_components(images,cnm.params,dview=dview)
        cnm.estimates.select_components(use_object=True)
    else:
        print("not evaluating components")

    data_moviepath = os.path.join(output_loc,data_noext)

    try:
        cnm.save(data_moviepath+'_cnmf_obj.hdf5')
    except ValueError as e:    
        print("Ran into error while saving:")
        print(e)

    np.savez(data_moviepath+"A.npz",cnm.estimates.A)
    np.savez(data_moviepath+"C.npz",cnm.estimates.C)
    np.savez(data_moviepath+"R.npz",cnm.estimates.R)
### Additionally get the new mmap file for refitting:
#Yr,dims,T = cm.load_memmap(cnm.mmap_file)
#d1,d2 = dims
#images = np.reshape(Yr.T,[T]+list(dims),order="F")
#
#t_patch = time.time() - t1
#try:
#    dview.terminate()
#except:
#    pass
#
#c, dview,n_processes = cm.cluster.setup_cluster(
#        backend=backend_refine,n_processes=n_processes,single_thread=False)
#
### Update some parameters
#cnm.params.change_params({'update_background_components':True,'skip_refinement':False,'n_pixels_per_process':n_pixels_per_process,'dview':dview})
#
### Refine:
#t1 = time.time()
#cnm2 = cnm.refit(images,dview=dview)
#t_refit = time.time()-t1
#
### Throw away bad components: 
#cnm2.estimates.evaluate_components(images,cnm2.params,dview=dview)
#cnm2.estimates.select_components(use_object=True)
#
### Save A, C, and residuals: 
#data_moviepath = os.path.join(output_loc,data_noext)
#print(output_loc,data_noext,"REL VARS")
### TODO: Move this to later: 
#
###  

