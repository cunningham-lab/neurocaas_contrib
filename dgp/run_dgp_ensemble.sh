execpath="$0"
scriptpath="$neurocaasrootdir/ncap_utils"

source "$scriptpath/workflow.sh"

## Import functions for data transfer 
source "$scriptpath/transfer.sh"

errorlog

call_proj_init () {
    echo "Project init $1"
    python "../neurocaas_ensembles/project_init.py"
}

datastore="deepgraphpose/data/ensembles"
configstore="ncapdata/configs"
outstore="ncapdata/localout"
taskname=$(basename $dataname .zip)

source "$userhome/.dlamirc"

export PATH="/home/ubuntu/anaconda3/bin:$PATH"

source activate dgp

accessdir "$userhome/$configstore"
accessdir "$userhome/$outstore"

aws s3 cp "s3://$bucketname/$inputpath" "$userhome/$datastore/"
aws s3 cp "s3://$bucketname/$configpath" "$userhome/$configstore/"
unzip -o "$userhome/$datastore/$dataname" -d "$userhome/$datastore/"

## read in important metadata from config: 
task,scorer,jobnb,videotype=$(python configscript.py "$userhome/$configstore/")

## create project from raw data: 
python project_init.py "$task" "$scorer" "2030-01-0$jobnb" "$userhome/$datastore" 

## Run dgp: 
cd "$userhome/deepgraphpose"
python "demo/run_dgp_demo.py" --dlcpath "$userhome/$datastore/$task-$scorer-2030-01-0$jobnb/"

aws s3 sync "$userhome/$datastore/$taskname/$task-$scorer-2030-01-0$jobnb/" "s3://$bucketname/$groupdir/$processdir/$jobnb/"
