#!/bin/bash
## Get execution directory of script. Assume it lives in ncap_remote
remotedir="$(dirname "$0")"

## Function to set error handling behavior for the function. 
errorlog () {
    set -e
    ## Get the last command for debugging.
    trap 'last_command=$current_command; current_command=$BASH_COMMAND' DEBUG
    ## echo an error message before exiting. 
    trap 'echo "\"${current_command}\" command filed with exit code $?."' EXIT
}

## Function to create a directory and give universal read write execute permissions to it. 
accessdir () {
    for var in "$@"
    do
        sudo mkdir -p "$var"
        sudo chmod 777 "$var"
    done
} 

## Function to create useful global variables from inputs to bash script in known way given command sent by SSM RunCommand as indicated in stackconfig.  
## Creates 4 path variables relating to the path of data as referenced in the source S3 bucket [bucketname,inputpath,grouppath,resultpath], and two as will be referenced locally [dataname,configname]. Does handling to ensure that we can manage folder uploads.  
parseargsstd () {
    bucketname="$1"
    inputdir="$(python "$remotedir"/ncap_utils/parse.py "$2")"
    groupdir="$(dirname "$inputdir")"
    resultdir="$3"
    dataname="$(basename "$2")"
    configname="$(basename "$4")"
    inputpath="$2"
    configpath="$4"
}

## Function to cleanup after all processing is done. Beware this function, as it will delete all foldernames passed as input and also power down the instance. 
cleanup () {
    for var in "$@"
    do 
        rm -r "$var"
    done 
    sudo poweroff
}
