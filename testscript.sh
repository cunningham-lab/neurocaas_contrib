#!/bin/bash

trap 'echo $BASH_COMMAND' EXIT

source /home/ubuntu/ncap_remote/ncap_utils/workflow.sh

#errorlog_cont
parseargsstd "$1" "$2" "$3" "$4"
echo "$bucketname"/"$groupdir"/"$resultdir"/logs/DATASET_NAME:"$dataname"_STATUS.txt"" 
errorlog_init 

echo "doing"

echo "random"

echo "stuff"

sleep 5

easdfljksdfa

errorlog_final
