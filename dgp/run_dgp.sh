execpath="$0"
scriptpath="$neurocaasrootdir/ncap_utils"

source "$scriptpath/workflow.sh"

## Import functions for data transfer 
source "$scriptpath/transfer.sh"

errorlog

userhome="/home/ubuntu"
datastore="deepgraphpose/data"
outstore="ncapdata/localout"
taskname=$(basename $dataname .zip)

source "$userhome/.dlamirc"

export PATH="/home/ubuntu/anaconda3/bin:$PATH"

source activate dgp

accessdir "$userhome/$outstore"


aws s3 cp "s3://$bucketname/$inputpath" "$userhome/$datastore/"
unzip -o "$userhome/$datastore/$dataname" -d "$userhome/$datastore/"

python "$neurocaasrootdir/dgp/project_path.py" "$userhome/$datastore/$taskname/config.yaml"

cd "$userhome/deepgraphpose"
python "demo/run_dgp_demo.py" --dlcpath "$userhome/$datastore/$taskname/"
aws s3 sync "$userhome/$datastore/$taskname/videos_pred/" "s3://$bucketname/$groupdir/$processdir"
