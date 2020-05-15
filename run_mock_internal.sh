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
#source .dlamirc

export PATH="/home/ubuntu/anaconda3/bin:$PATH"

source activate epi

## Declare local storage locations: 
userhome="/home/ubuntu"
datastore="epi/scripts/localdata/"
configstore="/home/ubuntu/" 
outstore="mock_results/"
## Make local storage locations
accessdir "$userhome/$datastore" "$userhome/$outstore"

## Stereotyped download script for data. The only reason this comes after something custom is because we depend upon the AWS CLI and installed credentials. 
download "$inputpath" "$bucketname" "$datastore"

## Stereotyped download script for config: 
download "$configpath" "$bucketname" "$configstore"

download "$configpath" "$bucketname" "$configstore"
echo $configstore $configname config parameters here
waittime=$(jq .wait "$configstore/$configname")
sleep $waittime


###############################################################################################
## Stereotyped upload script for the data
## give extensions to ignore. 
cd "mock_results"
aws s3 sync ./ "s3://$bucketname/$groupdir/$resultdir/process_results"
cd "/home/ubuntu/ncap_remote"
aws s3 cp ./end.txt "s3://$bucketname/$groupdir/$resultdir/process_results/end.txt"
#upload "$outstore" "$bucketname" "$groupdir" "$resultdir" "mp4"

#cleanup "$datastore" "$outstore"
