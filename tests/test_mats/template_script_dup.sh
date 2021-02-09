#!/bin/bash

## Import functions for workflow management. 
## Get the path to this function: 
execpath="$0"
echo execpath
scriptpath="$(dirname "$execpath")/ncap_utils"

source "$scriptpath/workflow.sh"

## Set up error logging. 
errorlog
