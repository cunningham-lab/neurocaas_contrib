## Installation 
Before installing the NeuroCAAS Contrib, you will need the following: 
- An installation of [Anaconda](https://docs.anaconda.com/anaconda/install/) or [Miniconda](https://docs.conda.io/projects/continuumio-conda/en/latest/user-guide/install/) to manage your python environment.  
- OPTIONAL FOR BETA FEATURES (An account on docker hub + a [docker](https://docs.docker.com/get-docker/) installation that gives you access to the docker cli. We will need these tools to pull an image from the neurocaas docker account and launch docker containers from the command line.) 

Once you have conda (and docker), download this repo from github, and move into it: 
```bash
`% git clone https://github.com/cunningham-lab/neurocaas_contrib`
`% cd path/to/your/neurocaas_contrib`
```

Now create and configure a conda environment as follows:  
```bash
% conda create -n neurocaas python=3.6.9 # create environment
% conda activate neurocaas # activate environment
% python -m pip install --upgrade pip # upgrade package manager
% pip install -r requirements.txt # install dependencies
% pip install ./src # install this repository
```
Remember to deactivate your conda environment when you are done (`conda deactivate neurocaas`). 
You can check if the install has gone smoothly by running the command `neurocaas_contrib --help` from the command line. You should see documentation for options and commands that you can append to this base command. If you experience any problems, please submit a new issue [here](https://github.com/cunningham-lab/neurocaas_contrib/issues).



