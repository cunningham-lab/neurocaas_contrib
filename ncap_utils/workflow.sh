#!/bin/bash
## Get execution directory of script. Assume it lives in ncap_remote
## NOTE: Most of these functions require you to run parseargsstd with appropriate aruments to function. 
echo "$0" workflow dirname

## Get the absolute path
abspath=$neurocaasrootdir
#abspath=$userhome/$remotedir

## Function to create useful global variables from inputs to bash script in known way given command sent by SSM RunCommand as indicated in stackconfig.  
## Creates 4 path variables relating to the path of data as referenced in the source S3 bucket [bucketname,inputpath,grouppath,resultpath], and two as will be referenced locally [dataname,configname]. Does handling to ensure that we can manage folder uploads.  
parseargsstd () {
    bucketname="$1"
    inputdir="$(python "$abspath"/ncap_utils/parse.py "$2")"
    groupdir="$(dirname "$inputdir")"
    resultdir="$3"
    processdir="$resultdir"/"process_results"
    dataname="$(basename "$2")"
    configname="$(basename "$4")"
    inputpath="$2"
    configpath="$4"
}

## Function to set error handling behavior for the function. 
errorlog () {
    set -e
    writepath="$abspath/ncap_utils/statusdict.json"
    tmp=$(mktemp)
    trap 'last_command=$current_command; current_command=$BASH_COMMAND; cat "$writepath" | jq --arg reason "$last_command" '"'"'.reason = [$reason]'"'"' > "$tmp" && mv "$tmp" "$writepath"' DEBUG	
}

errorlog_init () {
    ## Declare variables
    homepath="s3://"$bucketname"/"$groupdir"/"$resultdir"/logs/DATASET_NAME:"$dataname"_STATUS.txt"
    writepath="$abspath/ncap_utils/statusdict.json"

    ## Get the status file
    aws s3 cp  "$homepath" "$writepath" || cp "$abspath/ncap_utils/statusdict_template.json" "$writepath"
    chmod 777 "$writepath"

    ## Write to the status file    
    tmp=$(mktemp)
    cat "$writepath" | jq '.status = "IN PROGRESS"' > "$tmp" && mv "$tmp" "$writepath"

    ## Copy back
    aws s3 cp  "$writepath" "$homepath"
}

## to actually fetch data:
system_monitor () {
    homepath="s3://"$bucketname"/"$groupdir"/"$resultdir"/logs/DATASET_NAME:"$dataname"_STATUS.txt"
    writepath="$abspath/ncap_utils/statusdict.json"
    recent_usage=$(echo $[100-$(vmstat 1 2|tail -1|awk '{print $15}')])
    python "$abspath"/ncap_utils/log_background.py "$writepath" "$neurocaasrootdir"
    tmp=$(mktemp)
    cat "$writepath" | jq --arg usage $recent_usage '.cpu_usage = [$usage]' > "$tmp" && mv "$tmp" "$writepath" 
}

## Background process to start monitoring: 
errorlog_background () {
    homepath="s3://"$bucketname"/"$groupdir"/"$resultdir"/logs/DATASET_NAME:"$dataname"_STATUS.txt"
    writepath="$abspath/ncap_utils/statusdict.json"
    while true
    do
    sleep 10
    system_monitor
    aws s3 cp  "$writepath" "$homepath" --only-show-errors
    ## Also update the cert file: 
    python "$abspath"/ncap_utils/updatecert.py "$bucketname" "$groupdir"/"$resultdir"/logs/
    done
}

errorlog_final () {
    script_code="$?"
    homepath="s3://"$bucketname"/"$groupdir"/"$resultdir"/logs/DATASET_NAME:"$dataname"_STATUS.txt"
    writepath="$abspath/ncap_utils/statusdict.json"
    if [ $script_code -eq 0 ] 
    then 
        cat "$writepath" | jq '.status = "SUCCESS"' > "$tmp" && mv "$tmp" "$writepath"
        python "$abspath"/ncap_utils/log_background.py "$writepath" "$neurocaasrootdir"
        python "$abspath"/ncap_utils/finalcert.py "$bucketname" "$groupdir"/"$resultdir"/logs/ "$inputpath" "SUCCESS" 
    else 
        cat "$writepath" | jq '.status = "FAILED"' > "$tmp" && mv "$tmp" "$writepath";
        python "$abspath"/ncap_utils/log_background.py "$writepath" "$neurocaasrootdir"
        python "$abspath"/ncap_utils/finalcert.py "$bucketname" "$groupdir"/"$resultdir"/logs/ "$inputpath" "FAILED"
    fi
    aws s3 cp  "$writepath" "$homepath"
}

## Function to create a directory and give universal read write execute permissions to it. 
accessdir () {
    for var in "$@"
    do
        sudo mkdir -p "$var"
        sudo chmod 777 "$var"
    done
} 

## Function to log current progress
## Old log progress code. New code only uses python to parse output into json. 
#log_progress () {
#    output="$(python "$abspath"/ncap_utils/log.py "$bucketname" "$groupdir" "$dataname" "$resultdir" "$last_command" "$?")"
#}
## Python code to take a path to a status dictionary, and write in the newest parts of stdout and stderr
#log_progress () {
#    
#}


errorrep () {
    trap 'loc=$abspath; last_command=$current_command; current_command=$BASH_COMMAND; python "$abspath"/ncap_utils/log.py "$bucketname" "$groupdir" "$dataname" "$resultdir" "$BASH_COMMAND" ' DEBUG
    trap 'echo "\"$BASH_COMMAND\" command filed with exit code $?."' EXIT
}



## Function to cleanup after all processing is done. Beware this function, as it will delete all foldernames passed as input and also power down the instance. 
## Will work even if file does not exist. Shuts down the instance after 1 minute. 
cleanup () {
    for var in "$@"
    do 
        rm -r -f "$var"
    done 
    shutdown -h 1    
}
