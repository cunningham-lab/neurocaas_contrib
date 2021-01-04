# NeuroCAAS Contrib
## A repository to assist the creation of new analysis pipelines on the NeuroCAAS platform. 
This repository contains tools for development and maintenance of analyses to be used through the NeuroCAAS platform. It allows developers to first build their analyses on a docker container hosted on their local machine, then gradually transition it for use via drag-and-drop data upload, hosted on the cloud. 

## Installation 
Before installing the NeuroCAAS Contrib, you will need the following: 
- An account on docker hub + a [docker](https://docs.docker.com/get-docker/) installation that gives you access to the docker cli. We will need these tools to pull an image from the neurocaas docker account and launch docker containers from the command line. 
- An installation of [Anaconda](https://docs.anaconda.com/anaconda/install/) or [Miniconda](https://docs.conda.io/projects/continuumio-conda/en/latest/user-guide/install/) to manage your python environment.  

Once you have docker and conda, download this repo from github, and move into it: 
`% git clone https://github.com/cunningham-lab/neurocaas_contrib`
`% cd path/to/your/neurocaas_contrib`

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

## Setting up a development environment  
Once you've successfully installed NeuroCAAS Contrib, it's time to start developing. This is the process of taking some analysis code that you have written to process certain kinds of datasets, and making it usable through the NeuroCAAS platform. This process has three steps: 

- 1. Setting up an *immutable analysis environment*. First, we need to install and setup your analysis code in a portable environment that can be run on your local machine, or a virtual machine hosted on the cloud. We will do this by means of a pre-configured docker container. We call this an *immutable analysis environment* because no analysis user will be able to change it, other than by submitting data to be analyzed by means of scripts that you write.   
- 2. Setting up job management. Next, we need to make sure that users will be able to analyze all the different data types that you intend to offer, and that they will be seeing the output and logging information you want to make available. We have streamlined a lot of job management to make this process easy for you.   
- 3. Migrating to cloud resources. Finally, we want to make sure that the workflow you designed works on cloud resources (computing on cloud virtual machines, transferring data with cloud storage). This is where you might worry about configuring your analysis to work with a GPU, if that's necessary, or parallelizing across a multi-core machine.  

Before you start, it will be useful to have the following on hand: 
- 1. the code you need to run you analysis in some easy to install format (i.e. a Github repo)
- 2. some small example dataset you can use to quickly iterate through analysis runs. 

With your code and example dataset in hand, there are two ways to go through development workflow- through direct calls to the API (written in python) or the command line utility. We will describe both approaches in what follows.  

### Setting up an immutable analysis environment
First, we will set up a docker container where you can install your own analysis software, and save that to a new docker image (if these words don't mean much to you, don't worry). 

#### Working with the API (python console)
If you are working with the API, first start up a python interpreter inside your local environment, on your local machine (tested on ipython 7.7.0): 
`% ipython`
Now, import the neurocaas\_contrib.local module to start local development:
`>>> import neurocaas_contrib.local as local`

Instantiate a NeuroCAASImage object. This will create an object that manages the environment in which you install and setup your software.  
`>>> devimage = local.NeuroCAASImage()`

Now you can create an isolated local environment where you should install your software by running:

`>>> devimage.setup_container()`

This will print a message that you can connect to a container, neurocaasdevcontainer, and give you commands to run so that you can connect to it. Go ahead and run that command from the command line in a separate window. (Do not close the ipython console if you can):   

`docker exec -it neurocaasdevcontainer /bin/bash`

You will now be moved to a containerized environment where you can install your software (you will see a different username). Note that in this environment, we have already installed neurocaas\_contrib, as well as an additional directory called io-dir. We will cover the function of this directory next. Go ahead and install and setup your analysis software in this container. 

If you have previously launched a container through the API, you may run into an error message (409 Client Error: Conflict). In this case run the following from the command line to delete your previously created container: 

```bash
% docker container rm -f neurocaasdevcontainer`
```

Once you have installed your analysis software, you can save the container where you have installed your software to a new image by calling the following method in the console:  
`>>> devimage.save_container_to_image(tag)`

Where tag is a unique identifier of your analysis name and its current state (example "pcadev.[datetime]") 


#### Working with the CLI (todo)



