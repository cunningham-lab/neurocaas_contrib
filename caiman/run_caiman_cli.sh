#!/bin/bash
set -e
# Custom setup for this workflow.
#source .dlamirc
#
#export PATH="/home/ubuntu/anaconda3/bin:$PATH"
#
#source activate caiman
## Declare local storage locations: 
userhome="/home/ubuntu"
neurocaasrootdir="$userhome/neurocaas_remote/"
datastore="ncapdata/localdata/"
configstore="ncapdata/localconfig/"
outstore="ncapdata/localout/"

echo "----DOWNLOADING DATA----"
## Stereotyped download script for data. The only reason this comes after something custom is because we depend upon the AWS CLI and installed credentials. 
#download "$inputpath" "$bucketname" "$datastore"
neurocaas-contrib workflow get-data -f -o $userhome/$datastore/
## Stereotyped download script for config: 
#download "$configpath" "$bucketname" "$configstore"
neurocaas-contrib workflow get-config -f -o $userhome/$configstore/
## Check if it's yaml, and if so convert to json: 
## Reset to correctly get out json:

datapath=$(neurocaas-contrib workflow get-datapath)
configpath=$(neurocaas-contrib workflow get-configpath)
dataname=$(neurocaas-contrib workflow get-dataname)
configname=$(neurocaas-contrib workflow get-configname)

echo "----DATA DOWNLOADED: $datapath. PARSING PARAMETERS.----"
configname=$(python $neurocaasrootdir/ncap_utils/yamltojson.py "$configpath")

###############################################################################################
## Custom bulk processing. 
cd "$neurocaasrootdir"
export CAIMAN_DATA="/home/ubuntu/caiman_data"
## For efficiency: 
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
CAIMAN_DATA="$userhome/caiman_data"
python "$neurocaasrootdir"/caiman/parse_config_caiman.py "$bucketname" "$configpath" "$userhome/$configstore"
echo "----PARAMETERS PARSED. STARTING ANALYSIS----"
python "$neurocaasrootdir"/caiman/process_caiman.py "$configstore/final_pickled_new" "$datapath" "$userhome/$outstore" "$configpath"
echo "----ANALYSIS FINISHED. GENERATING VIDEO----"
python "$neurocaasrootdir/caiman/make_videos.py" --dirpath "$userhome/$outstore" --dataname "$dataname"
###############################################################################################
## Stereotyped upload script for the data
echo "----UPLOADING RESULTS----"
neurocaas-contrib workflow put-result -r "$userhome/$outstore"
