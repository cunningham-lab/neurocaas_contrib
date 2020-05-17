#!/bin/bash
# usage: sync_output outdir logdir bucketpath_outdir bucketpath_logdir tmpdir

# Copy Results Back To S3 Subdirectory
while [ -d "$2" ]; 
do
    echo -n "Last sync at ">>$2/checksync.txt;
    date >>$2/checksync.txt;
    aws s3 sync $1 $3;
    aws s3 sync $2 $4;
    if [ -f "$2/errorlog.txt" ]
    then
        echo -n "Error!" >>$2/checksync.txt;
        # Remove Temporary File Structure
        rm -rf $5
        shutdown -h now
    fi
    sleep 30;
done
