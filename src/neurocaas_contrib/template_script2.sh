#!/bin/bash
set -e 

## activate env. 
source activate env
neurocaas-contrib workflow initialize-job "dataset location"

# parse the relevant data names, and create the environment variables for them. 
## what if neurocaas-contrib can get these vars? 
neurocaas-contrib workflow register-dataset -b $1 -k $2 # creates $dataname, $datapath
neurocaas-contrib workflow register-config -b $1 -k $4 # creates $dataname, $datapath
neurocaas-contrib workflow register-file -n "name" -b $1 -k path # creates $dataname, $datapath
neurocaas-contrib workflow register-resultpath -b $1 -k $3

neurocaas-contrib workflow log-process $5 

neurocaas-contrib workflow cleanup # send config and end.txt. 

