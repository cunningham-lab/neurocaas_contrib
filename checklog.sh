#!/bin/bash

## Custom setup for this workflow.
source .dlamirc

export PATH="/home/ubuntu/anaconda3/bin:$PATH"

source activate dlcami
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

log_progress
