#!/bin/bash
## Bash script that establishes ncap monitoring routines with minimal dependencies on other packages. 
## Load in helper functions. 
execpath="$0"
echo execpath
scriptpath="$(dirname "$execpath")/ncap_utils"

source "$scriptpath/workflow.sh"
## Import functions for data transfer 
source "$scriptpath/transfer.sh"

## Now parse arguments in to relevant variables. These will be available to all scripts run from within. 
# Bucket Name  $bucketname
# Group Directory $groupdir 
# Results Directory $resultdir
# Dataset Name (without path) $dataname
# Dataset Full Path $datapath
# Configuration Name # configname
# Configuration Path # configpath
set -a
parseargsstd "$1" "$2" "$3" "$4"
set +a

echo $bucketname >> "/home/ubuntu/check_vars.txt.txt" 
echo $groudir >> "/home/ubuntu/check_vars.txt.txt" 
echo $resultdir >> "/home/ubuntu/check_vars.txt.txt" 
echo $dataname >> "/home/ubuntu/check_vars.txt.txt" 
echo $datapath >> "/home/ubuntu/check_vars.txt.txt" 
echo $configname >> "/home/ubuntu/check_vars.txt.txt" 
echo $configpath >> "/home/ubuntu/check_vars.txt.txt" 
 
## Set up Error Status Reporting:
errorlog_init 

## Set up STDOUT and STDERR Monitoring:
errorlog_background & 
background_pid=$!
echo $background_pid, "is the pid of the background process"

## MAIN SCRIPT GOES HERE #####################
bash "$5" #/home/ubuntu/ncap_remote/run_yass.sh
##############################################
errorlog_final
kill "$background_pid"

