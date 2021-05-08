#!/bin/bash
## From start to finish. 
execpath="$0"
scriptpath="$neurocaasrootdir/ncap_utils"

source "$scriptpath/workflow.sh"

## Import functions for data transfer 
source "$scriptpath/transfer.sh"

errorlog

call_read_label () {
    echo "compress labels for $1"	
    python read_manual_labels.py $1
}

call_proj_init () {
    echo "Project init $1"
    python "../neurocaas_ensembles/project_init.py"
}

datastore="ncapdata/localdata"
configstore="ncapdata/localconfig"
outstore="ncapdata/localout"

source .dlamirc

export PATH="/home/ubuntu/anaconda3/bin:$PATH"

source activate dgp

accessdir "$userhome/$datastore"
accessdir "$userhome/$configstore"
accessdir "$userhome/$outstore"

aws s3 cp "s3://$bucketname/$inputpath" "$userhome/$datastore/"
aws s3 cp "s3://$bucketname/$configpath" "$userhome/$configstore/"
## first unzip the training folder. 
datafolder=$(neurocaas-contrib scripting parse-zip -z "$userhome/$datastore/$dataname")
## get the manual labels: 
## read in important metadata from config: 
task=$(neurocaas-contrib scripting read-yaml -p "$userhome/$configstore/$configname" -f "task")
scorer=$(neurocaas-contrib scripting read-yaml -p "$userhome/$configstore/$configname" -f "scorer")
jobnb=$(neurocaas-contrib scripting read-yaml -p "$userhome/$configstore/$configname" -f "jobnb")
videotype=$(neurocaas-contrib scripting read-yaml -p "$userhome/$configstore/$configname" -f "videotype")
testing=$(neurocaas-contrib scripting read-yaml -p "$userhome/$configstore/$configname" -f "testing")
nb_frames=$(neurocaas-contrib scripting read-yaml -p "$userhome/$configstore/$configname" -f "nb_frames" -d "")
seed=$(neurocaas-contrib scripting read-yaml -p "$userhome/$configstore/$configname" -f "seed" -d "")

python neurocaas_ensembles/read_manual_labels.py "$userhome/$datastore/$datafolder" "$userhome/$datastore/" ".$videotype"
## This creates a folder called raw_data in the datastore folder. 
#unzip -o "$userhome/$datastore/$dataname" -d "$userhome/$datastore/"


## create project from raw data: 
python neurocaas_ensembles/project_init.py "$task" "$scorer" "2030-01-0$jobnb" "$userhome/$datastore/" "$nb_frames" "$seed"

## Run dgp: 
cd "$userhome/deepgraphpose"
if [ $testing == "True" ]
then
    python "demo/run_dgp_demo.py" --dlcpath "$userhome/$datastore/model_data/$task-$scorer-2030-01-0$jobnb/" --test
elif [ $testing == "False" ]    
then 	
    python "demo/run_dgp_demo.py" --dlcpath "$userhome/$datastore/model_data/$task-$scorer-2030-01-0$jobnb/" 
else    
    echo "Mode $testing not recognized. Valid options are "True" or "False". Exiting."	
    exit
fi    

aws s3 sync "$userhome/$datastore/model_data/$task-$scorer-2030-01-0$jobnb/" "s3://$bucketname/$groupdir/$processdir/$jobnb/"
