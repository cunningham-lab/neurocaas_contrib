#!/bin/bash

## Import functions for workflow management. 
## Get the path to this function: 
execpath="$0"
echo execpath
scriptpath="$neurocaasrootdir/ncap_utils"

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
## Check if it's yaml, and if so convert to json: 
## Reset to correctly get out json:
configname=$(python $neurocaasrootdir/ncap_utils/yamltojson.py "$userhome"/"$configstore"/"$configname")

###############################################################################################
## parse the config to place model folder, myconfig_analysis, in the right places. 
## First figure out if we're in training or test mode. 
analysismode=$(cat "$userhome/$datastore/$configname" | jq '.mode' | sed 's/"//g')
if [ $analysismode == "test" ] 
then
    echo testing 
    modelpath=$(cat "$userhome/$datastore/$configname" | jq '.modeldata.modelpath' | sed 's/"//g')
    configpath=$(cat "$userhome/$datastore/$configname" | jq '.modeldata.configpath' | sed 's/"//g')

    echo $modelpath modelpath
    echo $configpath configpath

    ## place python myconfig_analysis file and modelfolder in the right location.
    aws s3 sync "s3://""$bucketname"/"$modelpath" "$userhome/DeepLabCut/pose-tensorflow/models/"$(basename "$modelpath")""
    aws s3 cp "s3://""$bucketname"/"$configpath" "$userhome/DeepLabCut/myconfig_analysis.py"
    ## Replace the video location in the config folder. 
    python "neurocaas_remote/dlc/substitute_config.py"

    ## Preprocess videos 

    ## Run deeplabcut analysis: 
    cd DeepLabCut/Analysis-tools

    python AnalyzeVideos.py
    cd "$userhome"/"$datastore"

    find -iname "*.csv" -exec cp {} "$userhome"/"$outstore" \;
    find -iname "*.h5" -exec cp {} "$userhome"/"$outstore" \;
    find -iname "*.pickle" -exec cp {} "$userhome"/"$outstore" \;

    ## Copy:
    cd "$userhome"
elif [ $analysismode == "train" ]
then 
    echo training
    trainpath=$(cat "$userhome/$datastore/$configname" | jq '.traindata.trainpath' | sed 's/"//g')
    trainname=$(basename $trainpath)
    trainconfigpath=$(cat "$userhome/$datastore/$configname" | jq '.traindata.configpath' | sed 's/"//g')
    cp "$userhome/$datastore/$dataname" "$userhome/DeepLabCut/Generating_a_Training_Set"
    aws s3 cp "s3://$bucketname/$trainconfigpath" "$userhome/DeepLabCut/myconfig.py"
    cd "$userhome/DeepLabCut/Generating_a_Training_Set"
    unzip $dataname
    ## Go to the generating a training set diretory. 
    cd "$userhome/DeepLabCut/Generating_a_Training_Set/"
    python Step2_ConvertingLabels2DataFrame.py
    python Step3_CheckLabels.py
    python Step4_GenerateTrainingFileFromLabelledData.py
    # Copy labeled frames back to the user if they exist. 
    cp -r "$userhome/DeepLabCut/Generating_a_Training_Set/$trainname" "$userhome/$outstore/$trainname"
    aws s3 sync "$userhome/DeepLabCut/Generating_a_Training_Set/$trainname" "s3://$bucketname/$groupdir/$processdir/$trainname" 
    ## Now move the results to the model folder. 
    cd "$userhome/neurocaas_remote"
    foldername=$(python dlc/dlc_move_training_data.py)
    ## Now download the pretrained weights: 
    cd "$userhome/DeepLabCut/pose-tensorflow/models/pretrained"
    bash download.sh
    cd "$userhome/DeepLabCut/pose-tensorflow/models/$foldername/train"
    python ../../../train.py
    aws s3 sync "$userhome/DeepLabCut/pose-tensorflow/models/$foldername" "s3://$bucketname/$groupdir/$processdir/$foldername"
    
else
    echo "Mode $analysismode not recognized. Valid options are train or test. Exiting"
    exit
fi 
###############################################################################################
## Stereotyped upload script for the data
upload "$outstore" "$bucketname" "$groupdir" "$processdir" "mp4"

