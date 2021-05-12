#!/bin/bash
userhome="/home/ubuntu"
datastore="deepgraphpose/data"
outstore="ncapdata/localout"

source activate dgp
neurocaas-contrib workflow get-data -d -f -o $userhome/$datastore/
neurocaas-contrib workflow get-config -d -f -o $userhome/$datastore/

datapath=$(neurocaas-contrib workflow get-datapath)
configpath=$(neurocaas-contrib workflow get-configpath)
taskname=$(neurocaas-contrib scripting parse-zip -z "$datapath")

python "/home/ubuntu/neurocaas_contrib/dgp/project_path.py" "$userhome/$datastore/$taskname/config.yaml"

cd "$userhome/deepgraphpose"
python "demo/run_dgp_demo.py" --dlcpath "$userhome/$datastore/$taskname/"
zip "/home/ubuntu/results.zip" "$userhome/$datastore/$taskname/videos_pred/"
neurocaas-contrib workflow put-result -r "/home/ubuntu/results.zip" -d 
#aws s3 sync "$userhome/$datastore/$taskname/videos_pred/" "s3://$bucketname/$groupdir/$processdir"
