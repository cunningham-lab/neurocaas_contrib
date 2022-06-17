#!/bin/bash

execpath="$0" # get path to this script
scriptpath="$(dirname $(dirname "$execpath"))/ncap_utils" # get path to the utility library. 

## Import functions for workflow management. 
source "$scriptpath/workflow.sh" # import workflow management (monitoring, error finding) functions 
## Import functions for data transfer 
source "$scriptpath/transfer.sh" # import data transfer functions

## Set up error logging. 
errorlog #set up error logging

export PATH="/home/ubuntu/anaconda3/bin:$PATH" # environment setup

source activate epi # environment setup

## Declare local storage locations: 
userhome="/home/ubuntu" #declaring variables 
datastore="epi/scripts/localdata/" #declaring variables
configstore="epi/scripts/localconfig/" #declaring variables
#outstore="epi/scripts/data/lds_2D_linear2D_freq/" #declaring variables
outstore="epi/scripts/data/" #declaring variables
## Make local storage locations
accessdir "$userhome/$datastore" "$userhome/$configstore" "$userhome/$outstore" #initializing local storage locations

## Stereotyped download script for data. The only reason this comes after something custom is because we depend upon the AWS CLI and installed credentials. 
download "$inputpath" "$bucketname" "$datastore" #downloading data to immutable analysis environment

## Stereotyped download script for config: 
download "$configpath" "$bucketname" "$configstore" # downloading config to immutable analysis environment 

###############################################################################################
## Custom bulk processing. 
cd epi/scripts # going to script directory 

bash lds_hp_search_ncap.sh "$userhome"/"$datastore""$dataname" # script in EPI to run EPI optimization for given random seed. 

export resultsstore="data/lds_2D_*" # export result directory. 

## copy the output to our results directory: 
cd $resultsstore  # go to result directory. 
echo $PWD "working directory"
echo  "results aimed at" "s3://$bucketname/$groupdir/$processdir/" # report to user through stdout
aws s3 sync ./ "s3://$bucketname/$groupdir/$processdir/per_hp" # upload back to user. 

###############################################################################################
