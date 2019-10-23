#!/bin/bash
## Function to import data from an S3 bucket. Relies upon a python library included in this repo. 
## Takes as arguments the full path to the data in the s3 bucket, the bucket name, and the location we should write the data to. 
remotedir="$(dirname "$0")"
download () {
    python "$remotedir/ncap_utils/transfer_codebase/Download_S3_single.py" "$1" "$2" "$3" 
}

## Function to upload data back to S3. Relies upon a python function included in this repo. 
## Takes as arguments the path to the results directory, the bucket name, the group name, the results folder name, and extensions we should ignore. 
upload () {
    python "$remotedir/ncap_utils/transfer_codebase/Upload_S3.py" "$1" "$2" "$3" "$4" "$5"
}
