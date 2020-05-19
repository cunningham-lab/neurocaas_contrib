#!/bin/bash

## Import functions for workflow management. 
## Get the path to this function: 
execpath="$0"
scriptpath="$(dirname "$execpath")/ncap_utils"

source "$scriptpath/workflow.sh"
## Import functions for data transfer 
source "$scriptpath/transfer.sh"

## Set up error logging. 
errorlog

## Declare variables: bucketname,inputpath,grouppath,resultpath,dataname,configname given standard arguments to bin script.
parseargsstd "$1" "$2" "$3" "$4"

## Declare local storage locations: 
userhome="/home/ubuntu"
datastore="ncapdata/localdata/"
outstore="ncapdata/localdata/analysis_vids/"
## Make local storage locations
accessdir "$userhome/$datastore" "$userhome/$outstore"

###############################################################################################
## Custom setup for this workflow.
export PATH="/home/ubuntu/anaconda3/bin:$PATH"
export CAIMAN_DATA="/home/ubuntu/caiman_data"
## For efficiency: 
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1

source activate caiman
###############################################################################################
## Stereotyped download script for data. The only reason this comes after something custom is because we depend upon the AWS CLI and installed credentials. 
echo "$inputpath/$dataname" 
download_folder "$inputpath/$dataname" "$bucketname" "$datastore"

## Stereotyped download script for config: 
echo "$inputpath/$dataname" 
download "$inputpath/$configname" "$bucketname" "$datastore"

###############################################################################################
## Additionally, download the cnn model we will use. 
download "$inputpath/cnn_model_online.h5"

## Download the configuration dictionary: 

## First, initialize the parameter dictionary from downloaded configuration dict.  

## 

###############################################################################################
## Stereotyped upload script for the data
#upload "$outstore" "$bucketname" "$grouppath" "$resultpath" "mp4"

#cleanup "$datastore" "$outstore"
