#!/bin/bash 
set -e 
### Bash script to wrap python script pca.py. Passes pca.py the appropriate paths to the dataset, configuration file, and path where results should be written. See pca.py for details 
## Move dataset and config file to the appropriate location
echo "--Moving data and config files into temporary directory--"
neurocaas-contrib workflow get-data
neurocaas-contrib workflow get-config

## Get the names of the datasets once they have been moved 
echo "--Parsing paths--"
datapath=$(neurocaas-contrib workflow get-datapath)
configpath=$(neurocaas-contrib workflow get-configpath)
resultpath=$(neurocaas-contrib workflow get-resultpath-tmp)

echo "--Running PCA--"
python pca.py $datapath $configpath $resultpath

echo "--Writing results--"
neurocaas-contrib workflow put-result -r $resultpath/pcaresults

