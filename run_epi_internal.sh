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
configstore="epi/scripts/localconfig/"
outstore="epi/scripts/data/lds_linear2D_freq_mu=0.00E+00_6.25E-02_6.28E+00_3.95E-01/"
## Make local storage locations
accessdir "$userhome/$datastore" "$userhome/$configstore" "$userhome/$outstore"

## Stereotyped download script for data. The only reason this comes after something custom is because we depend upon the AWS CLI and installed credentials. 
download "$inputpath" "$bucketname" "$datastore"

## Stereotyped download script for config: 
download "$configpath" "$bucketname" "$configstore"

###############################################################################################
## Custom bulk processing. 
cd epi/scripts

bash lds_hp_search_ncap.sh "$userhome"/"$datastore""$dataname"

export resultsstore=data/lds_linear2D_freq_mu=0.00E+00_6.25E-02_6.28E+00_3.95E-01

## copy the output to our results directory: 
cd $resultsstore 
echo  "results aimed at" "s3://$bucketname/$groupdir/$resultdir/"
aws s3 sync ./ "s3://$bucketname/$groupdir/$resultdir/"

cd $userhome
###############################################################################################
## Stereotyped upload script for the data
## give extensions to ignore. 
#upload "$outstore" "$bucketname" "$groupdir" "$resultdir" "mp4"

#cleanup "$datastore" "$outstore"
