#!/bin/bash

## Custom setup for this workflow.
source .dlamirc

export PATH="/home/ubuntu/anaconda3/bin:$PATH"

source activate dlcami
## Import functions for workflow management. 
## Get the path to this function: 
execpath="$0"
scriptpath="$neurocaasrootdir/ncap_utils"

source "$scriptpath/workflow.sh"
## Import functions for data transfer 
source "$scriptpath/transfer.sh"

## Set up error logging. 
errorlog

## Declare variables: bucketname,inputpath,grouppath,resultpath,dataname,configname given standard arguments to bin script.
parseargsstd "$1" "$2" "$3" "$4"

echo $inputdir 
echo $groupdir 

## Declare local storage locations: 
userhome="/home/ubuntu"
datastore="ncapdata/localdata/"
outstore="ncapdata/localdata/analysis_vids/"
## Make local storage locations
accessdir "$userhome/$datastore" "$userhome/$outstore"

###############################################################################################
## Custom setup for this workflow.
source .dlamirc

export PATH="/home/ubuntu/anaconda3/bin:$PATH"

source activate dlcami
###############################################################################################
## Stereotyped download script for data. The only reason this comes after something custom is because we depend upon the AWS CLI and installed credentials. 
download "$inputpath" "$bucketname" "$datastore"

## Stereotyped download script for config: 
download "$configpath" "$bucketname" "$datastore"

###############################################################################################

## Run deeplabcut analysis: 
cd "$userhome"/DeepLabCut/Analysis-tools

python AnalyzeVideos_new.py

## Custom post processing. 
cd "$userhome"/Video_Pipelining
python Polleux_Postprocess.py "$userhome/$datastore"

cd "$userhome"

###############################################################################################
## Stereotyped upload script for the data
upload "$outstore" "$bucketname" "$groupdir" "$resultdir/process_results" "mp4"

#cleanup "$datastore" "$outstore"
