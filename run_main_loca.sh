#!/bin/bash
## Bash script that establishes ncap monitoring routines with minimal dependencies on other packages. 
## Load in helper functions. 
execpath="$0"
echo execpath
scriptpath="$(dirname "$execpath")/ncap_utils"

source "$scriptpath/workflow.sh"
## Import functions for data transfer 
source "$scriptpath/transfer.sh"

## Now parse arguments in to relevant variables: 
# Bucket Name  $bucketname
# Group Directory $groupdir 
# Results Directory $resultdir
# Dataset Name $dataname
# Dataset Full Path $datapath
# Configuration Name # configname
# Configuration Path # configpath
set -a
parseargsstd "$1" "$2" "$3" "$4"
set +a

## Example usage:
echo "$bucketname"/"$groupdir"/"$resultdir"/logs/DATASET_NAME:"$dataname"_STATUS.txt"" 
## Set up Error Status Reporting:
errorlog_init 

## Set up STDOUT and STDERR Monitoring:
errorlog_background & 
background_pid=$!
echo $background_pid, "is the pid of the background process"

## MAIN SCRIPT GOES HERE #####################
bash /home/ubuntu/bin/run.sh $bucketname $groupdir inputs $resultdir $resultdir/logs $dataname atlas.mat $configname 
##############################################
exit
errorlog_final
kill "$background_pid"

