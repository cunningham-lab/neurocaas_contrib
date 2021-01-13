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


#### Working with the CLI 
If you are working with the CLI, first check that the cli is correctly set up. You can run 

`neurocaas_contrib --help` 

And you should see a help page detailing the different functionality available:     

![docs/images/help.png](docs/images/help.png)

With a working CLI, you must first record the algorithm you are working on by running:  

`neurocaas_contrib init` 

This command writes a config file at `~/.neurocaas_contrib_config.json`, and keeps track of your configuration parameters over the course of the session. You will be prompted to give the name of the analysis that you want to work on: 

![docs/images/init.png](docs/images/init.png)

If it does not exist, you will be prompted to create a new one. 

![docs/images/init_write.png](docs/images/init_write.png)

If you want to work on a different analysis, you can run the same command again.  

You can check that initialization was successful by running:

`neurocaas_contrib describe-analyses`

You will see a list of all the analyses available for development, as well as a star next to the one currently being worked on: 

![docs/images/describe-analyses.png](docs/images/describe-analyses.png)

Once you have initialized your CLI, to work with a particular analysis, you want to start the process of setting up your software in a development container to create an immutable analysis environment (IAE). Your development container is an isolated environment with limited access to the file system available on you computer, so you will need to take several steps through the CLI to make the relevant data and software available. 
To make your sample data and configuration parameters available through the CLI, run the following command:   

`neurocaas_contrib setup-inputs -d path/to/sample/data.txt -c path/to/sample/configuration/params.json`

By running this command, you will copy sample data and config files into a location initialized by running `neurocaas_contrib init`. You can pass multiple instances of either the -d or -c flags if you would like to set up multiple inputs or config files at a time. You can also omit either entry. You can skip this step, but you will not be able to access any other data files in your IAE if you do so.    
Next, you will want to start installing and setting up your software into your IAE. This is done interactively from inside the IAE.  Run the following: 

`neurocaas_contrib setup-development-container`

You will then recieve a prompt that tells you how to enter your development container:

![docs/images/setup-development-container.png](docs/images/setup-development-container.png)

Running the given command will drop you directly into the container from the command line, where you can install the relevant software and perform setup. You should see something like this:  

![docs/images/enter-container.png](docs/images/enter-container.png)

Note that the user name should change to neurocaasdev@container code, and you will be in the base environment again. Once you are done installing and setting up your analysis, you can close the window by entering `exit` or `ctrl-D`.   

You can then save your progress by running:

`neurocaas_contrib save-developed-image`

You will be prompted to enter a unique tag id to distinguish the work you did in the container (we recommend the short version of your current github commit id + the date, or something unique like that). You will be told if the image was saved successfully. You can also save containers other than the one most recently started using the `setup-development-container ` command by passing the --container option.
If you want to keep tweaking your container, run the entry command again:

`neurocaas_contrib enter-container`

Otherwise, if you want to delete you development container and start from the new image, run the setup command:  

`neurocaas_contrib setup-development-container`

The CLI records your most recently saved image, and will start a new container from it automatically. To start a container from a different image, you can pass the relevant docker image tag with the `--image` parameter.  


