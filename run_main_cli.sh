#!/bin/bash

source "/home/ubuntu/.dlamirc"
export PATH="/home/ubuntu/anaconda3/bin:$PATH"
source activate dgp

neurocaas-contrib workflow initialize-job -p /home/ubuntu/contribdata

neurocaas-contrib workflow register-dataset -b "$1" -k "$2"
neurocaas-contrib workflow register-config -b "$1" -k "$4"
neurocaas-contrib workflow register-resultpath -b "$1" -k "$3"

neurocaas-contrib workflow log-command -b "$1" -c "$5" -r "$3"

neurocaas-contrib workflow cleanup
