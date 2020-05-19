#!/bin/bash
source "/home/ubuntu/ncap_remote/ncap_utils/workflow.sh"

parseargsstd "$1" "$2" "$3" "$4"
errorlog_background & 
background_pid=$!
echo $background_pid, "is the pid of the background process"
