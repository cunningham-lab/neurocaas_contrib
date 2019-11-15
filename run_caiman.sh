#!/bin/bash

## Import functions for workflow management. 
## Get the path to this function: 
execpath="$0"
echo execpath
scriptpath="$(dirname "$execpath")/ncap_utils"

source "$scriptpath/workflow.sh"
## Import functions for data transfer 
source "$scriptpath/transfer.sh"

## Set up error logging. 
errorlog

## Declare variables: bucketname,inputpath,groupdir,resultdir,dataname,configname given standard arguments to bin script.
#parseargsstd "$1" "$2" "$3" "$4"

#errorrep
## Custom setup for this workflow.
source .dlamirc

export PATH="/home/ubuntu/anaconda3/bin:$PATH"

source activate caiman

## Declare local storage locations: 
userhome="/home/ubuntu"
datastore="ncapdata/localdata/"
configstore="ncapdata/localconfig/"
outstore="ncapdata/localout/"
## Make local storage locations
accessdir "$userhome/$datastore" "$userhome/$configstore" "$userhome/$outstore"

## Stereotyped download script for data. The only reason this comes after something custom is because we depend upon the AWS CLI and installed credentials. 
download "$inputpath" "$bucketname" "$datastore"

## Stereotyped download script for config: 
download "$configpath" "$bucketname" "$configstore"

###############################################################################################
## Custom bulk processing. 
cd ncap_remote
export CAIMAN_DATA="/home/ubuntu/caiman_data"
## For efficiency: 
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
CAIMAN_DATA="$userhome/caiman_data"
python parse_config.py "$bucketname" "$userhome/$configstore/$configname" "$userhome/$configstore"
python process.py "$userhome/$configstore/final_pickled" "$userhome/$datastore/$dataname" "$userhome/$outstore"
cd $userhome
###############################################################################################
## Stereotyped upload script for the data
upload "$outstore" "$bucketname" "$groupdir" "$resultdir" "mp4"

cleanup "$datastore" "$outstore"
