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
## Custom setup for this workflow.
source .dlamirc

export PATH="/home/ubuntu/anaconda3/bin:$PATH"

source activate dlcami

## Set up error logging. 
errorlog

## Declare local storage locations: 
userhome="/home/ubuntu"
datastore="ncapdata/localdata/"
outstore="ncapdata/localout/"
## Make local storage locations
accessdir "$userhome/$datastore" "$userhome/$outstore"

## Stereotyped download script for data. The only reason this comes after something custom is because we depend upon the AWS CLI and installed credentials. 
echo $inputpath $bucketname $datastore

download "$inputpath" "$bucketname" "$datastore"

## Stereotyped download script for config: 
download "$configpath" "$bucketname" "$datastore"

###############################################################################################
## parse the config to place model folder, myconfig_analysis, in the right places. 
## First figure out if we're in training or test mode. 
analysismode=$(cat "$userhome/$datastore/$configname" | jq '.mode' | sed 's/"//g')
if [ $analysismode == "test" ] 
then
    echo in test branch. 
    exit
    modelpath=$(cat "$userhome/$datastore/$configname" | jq '.modeldata.modelpath' | sed 's/"//g')
    configpath=$(cat "$userhome/$datastore/$configname" | jq '.modeldata.configpath' | sed 's/"//g')

    echo $modelpath modelpath
    echo $configpath configpath

    ## place python myconfig_analysis file and modelfolder in the right location.
    aws s3 sync "s3://""$bucketname"/"$modelpath" "$userhome/DeepLabCut/pose-tensorflow/models/"$(basename "$modelpath")""
    aws s3 cp "s3://""$bucketname"/"$configpath" "$userhome/DeepLabCut/myconfig_analysis.py"
    ## Replace the video location in the config folder. 
    python "ncap_remote/substitute_config.py"

    ## Preprocess videos 

    ## Run deeplabcut analysis: 
    cd DeepLabCut/Analysis-tools

    python AnalyzeVideos.py
    cd "$userhome"/"$datastore"

    find -iname "*.h5" -exec cp {} "$userhome"/"$outstore" \;
    find -iname "*.pickle" -exec cp {} "$userhome"/"$outstore" \;

    ## Copy:
    cd "$userhome"
elif [ $analysismode == "train" ]
then 
    echo training
else
    echo "Mode $analysismode not recognized. Valid options are train or test. Exiting"
    exit
fi 
###############################################################################################
## Stereotyped upload script for the data
upload "$outstore" "$bucketname" "$groupdir" "$resultdir" "mp4"

