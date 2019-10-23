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

## Declare local storage locations: 
userhome="/home/ubuntu"
datastore="ncapdata/localdata/"
outstore="ncapdata/localout/"
## Make local storage locations
accessdir "$userhome/$datastore" "$userhome/$outstore"

###############################################################################################
## Custom setup for this workflow.
source .dlamirc

export PATH="/home/ubuntu/anaconda3/bin:$PATH"

source activate dlcami
###############################################################################################
## Stereotyped download script for data. The only reason this comes after something custom is because we depend upon the AWS CLI and installed credentials. 
echo "$inputpath/$dataname" 
download "$inputpath/$dataname" "$bucketname" "$datastore"

## Stereotyped download script for config: 
echo "$inputpath/$dataname" 
download "$inputpath/$configname" "$bucketname" "$datastore"

###############################################################################################
## Import variables from the configuration file: 
read -r XS XA YS YA <<< $(jq -r .Coordinates[] "$userhome/$datastore/$configname")
read -r ext <<< $(jq -r .Ext "$userhome/$datastore/$configname")

#preprocess videos:

cd "$userhome/$datastore/" 
mkdir -p "$userhome/$datastore"analysis_vids
counter=0
for i in ./*"$ext" ; do 
ffmpeg -y -i "$i" -c copy -f "${ext#"."}" needle.h264
ffmpeg -y -r 40 -i needle.h264 -c copy $(basename "${i/"$ext"}").mp4
ffmpeg -i $(basename "${i/"$ext"}").mp4 -filter:v "crop=$XS:$XA:$YS:$YA" analysis_vids/$(basename ${i/"$ext"}cropped).mp4  
echo "file '$(basename "${i/"$ext"}")2.mp4'" >> output.txt
rm needle.h264
done 

ffmpeg -f concat -i output.txt -vcodec copy -acodec copy $((counter+1))Final.mp4

## Run deeplabcut analysis: 
cd ../../DeepLabCut/Analysis-tools

python AnalyzeVideos_new.py
## Custom bulk processing. 

###############################################################################################
## Stereotyped upload script for the data
upload "$outstore" "$bucketname" "$grouppath" "$resultpath" "mp4"

#cleanup "$datastore" "$outstore"
