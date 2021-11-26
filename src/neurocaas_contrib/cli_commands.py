## Mimicking cli structure given in remote-docker-aws repository. 
import subprocess
import datetime
import sys
import shutil
import click 
import json
import os
from .blueprint import Blueprint
from .local import NeuroCAASImage,NeuroCAASLocalEnv
from .scripting import get_yaml_field,parse_zipfile,NeuroCAASScriptManager,mkdir_notexists

## template location settings:
dir_loc = os.path.abspath(os.path.dirname(__file__))
template_dir= os.path.join(dir_loc,"template_mats") 
default_write_loc = os.path.join(dir_loc,"local_envs")
testmatdir = os.path.join(dir_loc,"stack_test_mats")

if "pytest" in sys.modules:
    mode = "test"
else:
    mode = "std"

if mode == "test":
    configname = ".neurocaas_contrib_config_test.json"
    configpath = os.path.join(template_dir,configname)
    ## "separate for data storage during actual runs"
    storagename = ".neurocaas_contrib_storageloc_test.json" 
    storagepath = os.path.join(template_dir,storagename)

else:    
    ## configuration file settings:
    configname = ".neurocaas_contrib_config.json"
    configpath = os.path.join(os.path.expanduser("~"),configname)
    storagename = ".neurocaas_contrib_storageloc.json" 
    storagepath = os.path.join(os.path.expanduser("~"),storagename)

def save_ami_to_cli(ami):
    """Save a dictionary representing the development history to the cli's config file.

    :param ami: NeuroCAAS Ami object
    """
    amiinfo = ami.to_dict()

    try:
        with open(configpath,"r") as f:
            config = json.load(f)
        config["develop_dict"] = amiinfo
    except FileNotFoundError:
        click.echo("NeuroCAAS Contrib config file not found. Exiting.")
        raise
    with open(configpath,"w") as f:
        json.dump(config,f,indent = 4)
        

def delete_ami_from_cli(develop_dict,force = False):
    """Clears instance and blueprint from cli's config file. 
    :param develop_dict: the development dictionary that holds details about development you have already done.  
    :returns: bool- whether or not deletion happened
    """
    from .remote import NeuroCAASAMI
    analysis = develop_dict["config"]["PipelineName"]
    instance = develop_dict["instance_id"]
    if instance is not None: 
        click.confirm("Detected an existing development session with instance {} for analysis {}. Delete session?".format(instance, analysis),abort = True)
        ## delete instance.
        try:
            ami = NeuroCAASAMI.from_dict(develop_dict)
            message = ami.terminate_devinstance(force)
            if message == "No state change.":
                return False
            else:
                try:
                    with open(configpath,"r") as f:
                        config = json.load(f)
                    config["develop_dict"] = None    
                except FileNotFoundError:    
                    click.echo("NeuroCAAS Contrib config file not found. Exiting.")
                    raise
                with open(configpath,"w") as f:
                    json.dump(config,f,indent=4)
                return True    
        except FileNotFoundError:
            # the stackconfig is in a different branch; if no config exists, we can forget about it. 
            return True
    else:     
        click.echo("No development instance detected. Resetting session.")

def create_ctx(ctx,location,analysis_name,develop_dict):
    """helper function to attempt to create as much of the context object as is available. 

    :param ctx: click context object, used to pass state to subcommands
    :param location: path to the base blueprint directory. (or None)
    :param analysis_name: name of the analysis we want to find in `location`. (or None)
    :param developdict: dictionary holding details of development (or None)
    """
    ctx.obj = {}
    ctx.obj["location"] = location
    ctx.obj["analysis_name"] = analysis_name
    ctx.obj["develop_dict"] = develop_dict

    try:
        ctx.obj["blueprint"] = Blueprint(os.path.join(location,analysis_name,"stack_config_template.json")) ## we can now reference the context object with the decorator pass_obj, as below. 
    except FileNotFoundError as e: ## A note here. Create_CTX is triggered with analysis and location parameters passed directly to the cli command.  
        raise click.ClickException("Blueprint for analysis {} not found in location {}. Run `neurocaas_contrib init` first".format(ctx.obj["analysis_name"],ctx.obj["location"]))
    return ctx

def create_test_dir(path):
    """Given an analysis location, creates a directory within it with testing resources that are configured correctly. 
    :param path: path to the analysis folder (location where `stack_config_template.json` files are stored).  
    """
    analysis_name = os.path.basename(path) 
    local_testfolder = os.path.join(path,"test_resources")
    os.mkdir(local_testfolder)
    test_filepaths = {"submitfile":os.path.join(testmatdir,"exampledevsubmit.json"),
                      "putevent":os.path.join(testmatdir,"s3_putevent.json"),
                      "main_env_vars":os.path.join(testmatdir,"main_func_env_vars.json"),
                      "cloudwatch_start":os.path.join(testmatdir,"cloudwatch_startevent.json"),
                      "cloudwatch_end":os.path.join(testmatdir,"cloudwatch_termevent.json"),
                      "computereport1":os.path.join(testmatdir,"computereport_1234567.json"),
                      "compuretreport2":os.path.join(testmatdir,"computereport_2345678.json")} 
    for filetype,filepath in test_filepaths.items():
        filename = os.path.basename(filepath)
        destination = os.path.join(local_testfolder,filename)
        with open(filepath,"r") as f:
            contents = json.load(f)
        if filetype == "putevent":
            contents["Records"][0]["s3"]["bucket"]["name"] = analysis_name
            contents["Records"][0]["s3"]["bucket"]["arn"] = "arn:aws:s3:::{}".format(analysis_name)
        elif filetype == "main_env_vars":    
            contents["FigLambda"]["BUCKET_NAME"] = analysis_name 
        with open(destination,"w") as f:    
            json.dump(contents,f)
                
def set_important_options(analysis_blueprint):
    """Given an path to an analysis blueprint, asks the user for values to update that blueprint and updates. . 

    :param analysis_blueprint: path to analysis blueprint. 
    """
    with open(analysis_blueprint,"r") as f:
        blueprint_full = json.load(f)
    blueprint_defaults = {"Analysis Name":blueprint_full["PipelineName"],
            "Stage":blueprint_full["STAGE"],
            "Ami":blueprint_full["Lambda"]["LambdaConfig"]["AMI"],
            "Instance Type": blueprint_full["Lambda"]["LambdaConfig"]["INSTANCE_TYPE"]}
    for k,default in blueprint_defaults.items():
        value = click.prompt("Enter value for parameter {}".format(k),default = default)
        blueprint_defaults[k] = value
    blueprint_full["PipelineName"] = blueprint_defaults["Analysis Name"]
    blueprint_full["STAGE"] = blueprint_defaults["Stage"]
    blueprint_full["Lambda"]["LambdaConfig"]["AMI"] = blueprint_defaults["Ami"]
    blueprint_full["Lambda"]["LambdaConfig"]["INSTANCE_TYPE"] = blueprint_defaults["Instance Type"]
    with open(analysis_blueprint,"w") as f:
        json.dump(blueprint_full,f,indent = 4)


@click.group()
@click.option(
    "--location",
    help="Root location for neurocaas local environment build.", 
    default=None
        )
@click.option(
    "-a",   
    "--analysis-name",
    help="Name of the analysis you want to build.", 
    default=None)
@click.pass_context
def cli(ctx,location,analysis_name):
    """ Base command to interact with the neurocaas_contrib repo from the command line. Can be given location and analysis name parameters to run certain actions in a one-off manner, but preferred workflow is assigning these with the `init` subcommand. Assigns parameters (analysis metadata, blueprint, active image) to be referenced in other subparameters.  

    """
    ## Determine those commands for which you don't require a specific blueprint.
    no_blueprint = ['init','describe-analyses',"scripting","workflow"]
    try:
        with open(configpath,"r") as f:
            defaultconfig = json.load(f)

        if location is None or analysis_name is None:
            if location is None:
                location = defaultconfig["location"]
            if analysis_name is None:    
                analysis_name = defaultconfig["analysis_name"]
            develop_dict = defaultconfig.get("develop_dict",None)

        ctx = create_ctx(ctx,location,analysis_name,develop_dict)
    except (FileNotFoundError,click.ClickException,KeyError):    
        if ctx.invoked_subcommand in no_blueprint:
            return ## move on and run configure. 
        else:
            raise click.ClickException("Configuration file not found. Run `neurocaas_contrib init` to initialize the cli.")

@cli.command(help ="configure CLI to work with certain analysis.")
@click.option(
    "--location",
    help="Directory where we should store materials to develop this analysis. By default, this is: \n\b\n{}".format(default_write_loc), 
    default=None,
    type = click.Path(exists = True,file_okay = False,dir_okay = True,readable = True,resolve_path = True),
        )
@click.option(
    "--analysis-name",
    help="Name of the analysis you want to work on." ,
    prompt = True
        )
@click.pass_obj
def init(blueprint,location,analysis_name):
    """Configure CLI to work with certain analysis.

    Sets up the command line utility to work with a certain analysis by default. Must be run on first usage of the CLI, and run to create new analysis folders in given locations. If analysis folder does not yet exist, creates it.  
    """
    ## New Feature 1 (08/18/21): Use defaults for location:  
    if location is None:
        try:
            location = blueprint["location"] ## we expect this to be none if not given. 
        except (KeyError,TypeError):    
            click.echo("No location given and no previous location found. Defaulting to {} ".format(default_write_loc))
            location = default_write_loc

    analysis_location = os.path.join(location,analysis_name)
    ## Initialize state variables to determine whether or not we should write to the config file. 
    create = False
    initialize = False

    if not os.path.exists(analysis_location):
        create = click.confirm("The analysis named {} does not exist at {}. Initialize?".format(analysis_name,location),default = False)
        if create:
            os.mkdir(analysis_location) 
            ###Setup happens here
            template_blueprint = os.path.join(template_dir,"stack_config_template.json")
            analysis_blueprint = os.path.join(analysis_location,"stack_config_template.json")
            shutil.copyfile(template_blueprint,analysis_blueprint)
            ### add good options: 
            set_important_options(analysis_blueprint)

            create_test_dir(analysis_location)
        else:    
            print("Not creating analysis folder at this location.")
    elif not os.path.exists(os.path.join(analysis_location,"stack_config_template.json")):    
        initialize = click.confirm("The analysis named {} at {} is not correctly initialized. Initialize?".format(analysis_name,location),default = False)
        if initialize:
            ###Setup happens here
            template_blueprint = os.path.join(template_dir,"stack_config_template.json")
            analysis_blueprint = os.path.join(analysis_location,"stack_config_template.json")
            shutil.copyfile(template_blueprint,analysis_blueprint)
            ### add good options: 
            set_important_options(analysis_blueprint)
            create_test_dir(analysis_location)
        else:    
            print("Not creating analysis folder at this location.")
    else:        
        create = True
        initialize = True

    ## Only if you created or initialized an analysis folder should the config file be written to.
    if create or initialize:
        ## First set the analysis name in the config file:
        ## Reset the develop dict whenever we reinitialize. 
        analysis_settings = {"analysis_name":analysis_name,
                             "location":location,
                             "develop_dict":None
                            }
        ## Get dictionary:
        try:
            with open(configpath,"r") as f:
                config = json.load(f)
            config["analysis_name"] = analysis_name
            config["location"] = location
        except FileNotFoundError:
            click.echo("NeuroCAAS Contrib config file not found. Writing now.")
            config = analysis_settings
        with open(configpath,"w") as f:
            json.dump(config,f,indent = 4)


@cli.command(help ="list all analyses.")
@click.option(
    "--location",
    help="Directory where we should store materials to develop this analysis. By default, this is: \n\b\n{}".format(default_write_loc), 
    default=None,
    type = click.Path(exists = True,file_okay = False,dir_okay = True,readable = True,resolve_path = True)
        )
@click.pass_obj
def describe_analyses(context,location):
    """List all of the analyses available to develop on. Takes a location parameter: by default will be the packaged local_envs location. 

    """
    if location is None:
        try:
            location = context["location"] ## we expect this to be none if not given. 
        except (KeyError,TypeError):    
            click.echo("No location given and no previous location found. Defaulting to {} ".format(default_write_loc))
            location = default_write_loc
    all_contents = os.listdir(location) 
    dirs = [ac for ac in all_contents if os.path.isdir(os.path.join(location,ac))] 
    ## Add a star for the current one. 
    try:
        with open(configpath,"r") as f:
            config = json.load(f)
        currentanalysis = config["analysis_name"]    
        ## Todo 
    except FileNotFoundError:        
        currentanalysis = None
    dirs_searched = [d if currentanalysis != d else d+"*" for d in dirs]

    analyses = "\n".join(dirs_searched)
    analyses_formatted = "\nNeuroCAAS Analyses Available for Development: \n\n"+analyses + "\n"
    click.echo(analyses_formatted)

@cli.command(help = "print the current blueprint.")
@click.pass_obj
def get_blueprint(blueprint):
    """Prints the blueprint that CLI is currently configured to work with. Given in JSON format.  

    """
    string = json.dumps(blueprint["blueprint"].blueprint_dict,indent = 2)
    click.echo(string)

@cli.group(help = "develop locally in a docker container.")
def local():
    pass 

@local.command(help = "print information about the IAE from the blueprint.")
@click.pass_obj
def get_iae_info(blueprint):
    """Prints information about the IAE from the blueprint that CLI is currently configured to work with. Given in JSON format.  

    """
    active_container = blueprint["blueprint"].active_container_status
    active_image = blueprint["blueprint"].active_image
    script = blueprint["blueprint"].blueprint_dict.get("script",None)

    ## Check if the container is currently running: 

    container_history = [None,None] + blueprint["blueprint"].blueprint_dict.get("container_history",[None,None])
    image_history = [None,None] + blueprint["blueprint"].blueprint_dict.get("image_history",[None,None])   
    previous_container = container_history[-2]
    previous_image = image_history[-2]
    if active_container is None and active_image is None:
        click.echo("No info available.")
    else:    
        click.echo(f"\nCurrent IAE info: \n\nactive_container: {active_container}\nactive_image: {active_image}\nscript: {script}\nprevious_container: {previous_container}\nprevious_image: {previous_image}\n")

@click.option("-i",
        "--image",
        help = "base image tag to use as the start of development. If not given, reverts to entry in blueprint.",
        default = None)
@click.option("-c",
        "--container",
        help = "name to give to containers",
        default="neurocaasdevcontainer")
@local.command(help = "set up an environment to develop in.")
@click.pass_obj
def setup_development_container(blueprint,image,container):
    """Launches a container from an image of your choice so that you can perform configuration."""
    ## See if the blueprint has the fields you want:
    if image is None:
        image = blueprint["blueprint"].active_image
    
    envloc = blueprint["blueprint"].blueprint_dict.get("localenv",None)
    containerparams = {}
    if envloc is not None:
        ncle = NeuroCAASLocalEnv(envloc) 
        containerparams["env"] = ncle
    active_image = NeuroCAASImage(image,container)
    active_image.setup_container(**containerparams)
    blueprint["blueprint"].update_image_history(active_image.image_tag)
    blueprint["blueprint"].update_container_history(active_image.container_name)
    blueprint["blueprint"].write()

@local.command(help = "removes the current active container.")
@click.option("-c",
        "--container",
        help = "name of container to remove",
        default = None)
@click.pass_obj
def reset_container(blueprint,container):
    """Removes the currently active container. Useful if you want to launch from a new image. You can also remove a separate named container. Be careful, as you can lose progress if you reset a container that has not been saved into an image with `neurocaas_contrib save-development-container`   

    """
    if container is None:
        container = blueprint["blueprint"].active_container
    if container is None:    
        raise click.ClickException("Can't find container to reset.")
    image = NeuroCAASImage(None,None) 
    try:
        image.assign_default_container(container)
        image.current_container.remove(force = True)    
        click.echo(f"Container {container} removed. Safe to start a new one.")
    except Exception: 
        click.echo("Container not found. Run `setup-development-container` first.")

@local.command(help = "save a container to a new image.")
@click.option("-t",
        "--tagid",
        help = "unique tag identifier to identify this image. Will generate image name as neurocaas/contrib:[analysisname].[tagid]",
        prompt = True)
@click.option("-f",
        "--force",is_flag = True,
        help = "if true, overwrites existing image with this name.")
@click.option("-c",
        "--container",
        help = "name of the container to save.",
        default = None
        )
@click.option("-s",
        "--script",
        help = "path to script inside the container.",
        default = None
        )
@click.pass_obj
def save_developed_image(blueprint,tagid,force,container,script):
    """Saves a container into a new image, and saves that image as the new default for this analysis. """
    image = NeuroCAASImage(None,None) 
    if container is None:
        container = blueprint["blueprint"].active_container
    if container is None:    
        raise click.ClickException("No valid container can be found. Please provide one explicitly with --container")
    try:
        image.assign_default_container(container)
    except Exception: 
        click.echo("Container not found. Run `setup-development-container` first.")
        raise
    tag = "{}.{}".format(blueprint["analysis_name"],tagid)
    script_args = {}
    ## Check for default in the blueprint
    if script is None:    
        script = blueprint["blueprint"].blueprint_dict.get("script",None)
    ## If exists, write to blueprint too.    
    if script is not None:
        script_args["script"] = script
        blueprint["blueprint"].blueprint_dict["script"] = script
        blueprint["blueprint"].write()
    saved = image.save_container_to_image(tag,force,**script_args)
    if saved:
        blueprint["blueprint"].update_image_history("{}:{}".format(image.repo_name,tag))
        blueprint["blueprint"].write()

@local.command(help="enter the container to start development.")
@click.option("-c",
        "--container",
        help = "name of the container to enter.",
        default = None
        )
@click.pass_obj
def enter_container(blueprint,container):
    """Runs docker exec -it {containername} /bin/bash, connecting the terminal to your container. 

    """
    if container is None:
        container = blueprint["blueprint"].active_container
    if container is None:    
        raise click.ClickException("Can't find container to enter.")
    else:
        subprocess.run(["docker","exec","-it",container,"/bin/bash"])

@local.command(help = "prepare sample input data.")
@click.option("-d",
        "--data",
        help = "path to test dataset.",
        type = click.Path(exists = True,file_okay = True,dir_okay = True,readable = True,resolve_path = True),
        multiple = True)
@click.option("-c",
        "--config",
        help = "path to test config file.",
        type = click.Path(exists = True,file_okay = True,dir_okay = True,readable = True,resolve_path = True),
        multiple = True)
@click.pass_obj
def setup_inputs(blueprint,data,config):
    """Takes in the sample data you'd like to use, sets up a local environment, and deposits data and config there.   

    """
    ## Initialize the local environment:
    analysis_location = os.path.join(blueprint["location"],blueprint["analysis_name"])
    ncle = NeuroCAASLocalEnv(analysis_location) 
    ## Now deposit all data into the inputs directory:
    for dat in data:
        datname = os.path.basename(dat)
        shutil.copyfile(dat,os.path.join(analysis_location,"io-dir","inputs",datname))

    ## Deposit all configs into the config directory:
    for conf in config:
        confname = os.path.basename(conf)
        shutil.copyfile(conf,os.path.join(analysis_location,"io-dir","configs",confname))
    blueprint["blueprint"].blueprint_dict["localenv"] = analysis_location 
    blueprint["blueprint"].write()
    
@click.option("-i",
        "--image",
        help = "image to run analysis from.",
        default = None)
@click.option("-d",
        "--data",
        help = "name of the dataset you will analyze.",
        default = None,
        type = click.STRING)
@click.option("-c",
        "--config",
        help = "name of the config file you will analyze.",
        default = None,
        type = click.STRING)
@local.command(help = "run analysis in a saved environment.")
@click.pass_obj
def run_analysis(blueprint,image,data,config):
    """Launches a container from an image of your choice so that you can perform configuration."""
    ## See if the blueprint has the fields you want:
    if image is None:
        image = blueprint["blueprint"].active_image
   
    try:
        envloc = blueprint["blueprint"].blueprint_dict["localenv"]
    except KeyError:    
        raise click.ClickException("Inputs not configured. Run setup-inputs first.")

    ncle = NeuroCAASLocalEnv(envloc) 
    active_image = NeuroCAASImage(image,None)
    active_image.run_analysis_parametrized(data,config,ncle)
    ## we should probably write womething here... 

@cli.command(help = "go home")
def home():
    subprocess.run(["cd","/Users/taigaabe"])

def convert_folder_to_stackname(location,foldername):
    """Sometimes, especially for legacy functions there is a foldername as well as a stack name. Get the stack name from the location and foldername. 

    """
    stackconfig = os.path.join(location,foldername,"stack_config_template.json")
    ## get contents: 
    with open(stackconfig,"r") as f:
        stackdict = json.load(f) 
    return stackdict["PipelineName"]    

@cli.group()
@click.pass_context
def monitor(ctx):
    """Job monitoring functions.
    """

    from .monitor import calculate_parallelism, get_user_logs, postprocess_jobdict, JobMonitor
    moddict = {"calculate_parallelism":calculate_parallelism,"get_user_logs":get_user_logs,"postprocess_jobdict":postprocess_jobdict,"JobMonitor":JobMonitor}
    ctx.obj["monitormod"] = moddict 
    return

### cli commands to monitor the stack. 
@monitor.command(help = "visualize the degree of parallelism of analysis usage.")
@click.option("-p",
        "--path",
        type = click.Path(exists = True,dir_okay = True, file_okay = False,writable = True,resolve_path = True),
        help = "path to which we should write the resulting graphic.")
@click.option("-b",
        "--bucket_name",
        type = click.STRING,
        help = "name of the s3 bucket you want to list if not local.",
        default = None)
@click.pass_obj
def visualize_parallelism(blueprint,path,bucket_name):
    if bucket_name is None:
        analysis_name = convert_folder_to_stackname(blueprint["location"],blueprint["analysis_name"]) 
    else:    
        analysis_name = bucket_name
    user_dict = blueprint["monitormod"]["get_user_logs"](analysis_name)
    for user,userinfo in user_dict.items():
        parallelised = blueprint["monitormod"]["calculate_parallelism"](analysis_name,userinfo,user)
        postprocessed = blueprint["monitormod"]["postprocess_jobdict"](parallelised)
        now = str(datetime.datetime.now())
        write_path = os.path.join(path,f"{analysis_name}_{user}_{now}_parallel_logs.json")    
        with open(write_path,"w") as f:
            json.dump(postprocessed,f,indent = 4)
    
@monitor.command(help = "see users of a given analysis.")
@click.option("-s",
        "--stackname",
        type = click.STRING,
        default = None,
        help = "name of the stack folder that you want to get job manager requests for.")
@click.pass_obj
def see_users(blueprint,stackname):
    if stackname is None:
        analysis_name = blueprint["analysis_name"] 
    else:
        analysis_name = convert_folder_to_stackname(blueprint["location"],stackname)    
    user_dict = blueprint["monitormod"]["get_user_logs"](analysis_name)
    userlist = [u+ ": "+str(us) for u,us in user_dict.items()]
    formatted = "\n".join(userlist)
    click.echo(formatted)

@monitor.command(help = "print recent job manager requests.")    
@click.option("-s",
        "--stackname",
        type = click.STRING,
        default = None,
        help = "name of the stack folder that you want to get job manager requests for.")
@click.option("-h",
        "--hours",
        type = click.INT,
        help = "how many hours ago you want to start looking ",
        default = 1)
@click.option("-i",
        "--index",
        type = click.INT,
        help = "the index of request you want to get (0 = most recent)",
        default = 0)
@click.pass_obj
def describe_job_manager_request(blueprint,stackname,hours,index):
    """UNTESTED

    """
    if stackname is None:
        stackname = blueprint["analysis_name"] 
    else:    
        stackname = convert_folder_to_stackname(blueprint["location"],stackname)    
    jm = blueprint["monitormod"]["JobMonitor"](stackname)    
    jm.print_log(hours=hours,index=index)

@monitor.command(help = "print certificate file for submission. can give submitpath or groupname and timestamp.")    
@click.option("-s",
        "--stackname",
        type = click.STRING,
        default = None,
        help = "name of the stack folder that you want to get job manager requests for.")
@click.option("-p",
        "--submitpath",
        type = click.Path(exists = True,dir_okay = False, file_okay = True,writable = True,resolve_path = True),
        help = "path to submit file",
        default = None
        )
@click.option("-g",
        "--groupname",
        type = click.STRING,
        help = "name of the group we are getting certificate for",
        default = None
        )
@click.option("-t",
        "--timestamp",
        type = click.STRING,
        help = "timestamp of job.",
        default = None
        )
@click.pass_obj
def describe_certificate(blueprint,stackname,submitpath,groupname,timestamp):
    """UNTESTED

    """
    if stackname is None:
        stackname = blueprint["analysis_name"] 
    else:    
        stackname = convert_folder_to_stackname(blueprint["location"], stackname)    
    assert (submitpath is not None) or (groupname is not None and timestamp is not None), "must give certificate specs from submit or timestamp/groupname"     
    if submitpath is not None:
        jm = blueprint["monitormod"]["JobMonitor"](stackname)    
        cert = jm.get_certificate(submitpath)
        click.echo(cert.rawfile)
    elif (groupname is not None) and (timestamp is not None):     
        jm = blueprint["monitormod"]["JobMonitor"](stackname)    
        cert = jm.get_certificate_values(timestamp,groupname)
        click.echo(cert.rawfile)
    
    
@monitor.command(help = "print datasets being analyzed, and instances on which they are being analyzed.")    
@click.option("-s",
        "--stackname",
        type = click.STRING,
        default = None,
        help = "name of the stack folder that you want to get job manager requests for.")
@click.option("-p",
        "--submitpath",
        type = click.Path(exists = True,dir_okay = False, file_okay = True,writable = True,resolve_path = True),
        help = "path to submit file",
        )
@click.pass_obj
def describe_datasets(blueprint,stackname,submitpath):
    """UNTESTED

    """
    if stackname is None:
        stackname = blueprint["analysis_name"] 
    else:     
        stackname = convert_folder_to_stackname(blueprint["location"],stackname)    
    jm = blueprint["monitormod"]["JobMonitor"](stackname)    
    datasets = jm.get_datasets(submitpath)
    click.echo(datasets)

@monitor.command(help = "prints the datastatus of any given dataseet.")    
@click.option("-s",
        "--stackname",
        type = click.STRING,
        default = None,
        help = "name of the stack folder that you want to get job manager requests for.")
@click.option("-p",
        "--submitpath",
        type = click.Path(exists = True,dir_okay = False, file_okay = True,writable = True,resolve_path = True),
        help = "path to submit file",
        default = None
        )
@click.option("-g",
        "--groupname",
        type = click.STRING,
        help = "name of the group we are getting certificate for",
        default = None
        )
@click.option("-t",
        "--timestamp",
        type = click.STRING,
        help = "timestamp of job.",
        default = None
        )
@click.option("-d",
        "--dataname",
        type = click.STRING,
        help = "basename of dataset to get status for.",
        )
@click.option("-c",
        "--cutoff",
        type = click.INT,
        help = "cutoff for logs (c-end)",
        default = 0
        )
@click.pass_obj
def describe_datastatus(blueprint,stackname,submitpath,groupname,timestamp,dataname,cutoff):
    """UNTESTED

    """
    if stackname is None:
        stackname = blueprint["analysis_name"] 
    else:    
        stackname = convert_folder_to_stackname(blueprint["location"],stackname)    
    assert (submitpath is not None) or (groupname is not None and timestamp is not None), "must give certificate specs from submit or timestamp/groupname"     
    if submitpath is not None:
        jm = JobMonitor(stackname)    
        datastatus= jm.get_datastatus(submitpath,dataname)
    elif (groupname is not None and timestamp is not None):   
        jm = JobMonitor(stackname)    
        datastatus= jm.get_datastatus_values(groupname,timestamp,dataname)
    try:
        text = datastatus.rawfile.pop("std")
        list_text = [text[str(i)] for i in range(cutoff,len(text))]
        formattext = "".join(list_text)

        formatted = [str(key)+": "+str(value) for key,value in datastatus.rawfile.items()]
        formatted.append("std: "+formattext)
        lined = "\n".join(formatted)
        click.echo(lined)
    except KeyError: ## file isn't formatted as expected     
        click.echo(json.dumps(datastatus.rawfile,indent = 4))

## scripting tools 
@cli.group()
def scripting():
    """Scripting functions.
    """

    return 

@click.option("-p",
        "--path",
        help = "path to yaml file",
        type = click.Path(exists = True,file_okay = True,readable = True,resolve_path = True)
        )
@click.option("-f",
        "--field",
        help = "field to extract from yaml file"
        )
@click.option("-d",
        "--default",
        help = "default output to give if not found")
@scripting.command(help = "extract field from a yaml file as a string. If field is a list, will output into a bash array. ")
def read_yaml(path,field,default = None):
    try:
        output = get_yaml_field(path,field)
        print(output)
    except KeyError:    
        if default is None: 
            raise
        else:
            print(default)
    #click.echo(output)

@scripting.command(help ="extract zipped folder into the same directory, and echo basename of the folder that is extracted.")
@click.option("-z",
        "--zippath",
        help = "path to zip file",
        type = click.Path(exists = True,file_okay = True,readable = True,resolve_path = True)
        )
@click.option("-o",
        "--outpath",
        help = "directory in which to place the extracted directory- default to same directory.",
        type = click.Path(exists = True,dir_okay = True,readable = True,resolve_path = True),
        default = None
        )
def parse_zip(zippath,outpath):
    output = parse_zipfile(zippath,outpath)
    click.echo(output)


## workflow tools 
@cli.group(help = "tools to manage the transfer of data to and from this development")
@click.pass_context
def workflow(ctx):
    """Workflow functions.
    """
    ## If initializing job, we don't have to check for a storage file. Otherwise, complain that we need one. 
    if ctx.invoked_subcommand == "initialize-job":
        return
    else:
        try:
            with open(storagepath,"r") as f:
                storage = json.load(f)
        except FileNotFoundError:    
            raise click.ClickException("Storage file not found. Run `neurocaas_contrib workflow initialize-job` to initialize the cli.")
        try:
            storageloc = storage["path"]
        except KeyError:    
            raise click.ClickException("path not located in storage file. Run `neurocaas_contrib workflow initialize-job`")
        ctx.obj = {}
        ctx.obj["storage"] = storage
    return 

@workflow.command(help="initialize data transfer location")
@click.option("-p",
        "--path",
        help = "location where we will store and register data.",
        type = click.Path(exists = True,file_okay = False, dir_okay= True, resolve_path = True))
@click.pass_obj
def initialize_job(obj,path):
    """Initialize data storage location, and write to a storage file: 

    """
    storage = {}
    storage["path"] = path 
    ## create scriptmanager: 
    ncsm = NeuroCAASScriptManager(path)
    with open(storagepath,"w") as f:
        json.dump(storage,f)
        
@workflow.command(help="register a dataset for processing. Can be located locally (use -l) or in s3 (use -b, -k)")
@click.option("-b",
        "--bucket",
        help = "bucket where data is located",
        default = None,
        type = click.STRING)
@click.option("-k",
        "--key",
        help = "key of the file within the indicated bucket",
        default = None,
        type = click.STRING)
@click.option("-l",
        "--localpath",
        help = "local path where data is located.",
        default = None,
        type = click.STRING)
@click.pass_obj
def register_dataset(obj,bucket,key,localpath):        
    """Register a dataset with the scriptmanager. 

    """
    assert (bucket is not None and key is not None) ^ (localpath is not None), "you can pass either -b and -k (s3 file) or -l (local file)" 
    ## Get registration:
    path = obj["storage"]["path"]
    ncsm = NeuroCAASScriptManager.from_registration(path)
    if bucket is not None and key is not None:
        path = os.path.join("s3://",bucket,key)
        ncsm.register_data(path)
    elif localpath is not None:    
        ncsm.register_data_local(localpath)

@workflow.command(help="register a config file for processing. Can be located locally (use -l) or in s3 (use -b, -k)")
@click.option("-b",
        "--bucket",
        help = "bucket where config file is located",
        type = click.STRING)
@click.option("-k",
        "--key",
        help = "key of the file within the indicated bucket",
        type = click.STRING)
@click.option("-l",
        "--localpath",
        help = "local path where config is located.",
        default = None,
        type = click.STRING)
@click.pass_obj
def register_config(obj,bucket,key,localpath):        
    """Register a config file with the scriptmanager. 

    """
    assert (bucket is not None and key is not None) ^ (localpath is not None), "you can pass either -b and -k (s3 file) or -l (local file)" 
    ## Get registration:
    path = obj["storage"]["path"]
    ncsm = NeuroCAASScriptManager.from_registration(path)
    if bucket is not None and key is not None:
        path = os.path.join("s3://",bucket,key)
        ncsm.register_config(path)
    elif localpath is not None:    
        ncsm.register_config_local(localpath)

@workflow.command(help="register an arbitrary file for processing. can be located locally (use -l) or in s3 (use -b, -k)")
@click.option("-n",
        "--name",
        help = "name of file to reference later",
        type = click.STRING)
@click.option("-b",
        "--bucket",
        help = "bucket where file is located",
        type = click.STRING)
@click.option("-k",
        "--key",
        help = "key of the file within the indicated bucket",
        type = click.STRING)
@click.option("-l",
        "--localpath",
        help = "local path where file is located.",
        default = None,
        type = click.STRING)
@click.pass_obj
def register_file(obj,name,bucket,key,localpath):        
    """Register an arbitrary file with the scriptmanager. 

    """
    assert (bucket is not None and key is not None) ^ (localpath is not None), "you can pass either -b and -k (s3 file) or -l (local file)" 
    ## Get registration:
    path = obj["storage"]["path"]
    ncsm = NeuroCAASScriptManager.from_registration(path)
    if bucket is not None and key is not None:
        path = os.path.join("s3://",bucket,key)
        ncsm.register_file(name,path)
    elif localpath is not None:    
        ncsm.register_file_local(name,localpath)

@workflow.command(help="register a result path to store results. can be located locally (use -l) or in s3 (use -b, -k)")
@click.option("-b",
        "--bucket",
        help = "bucket where results should be located",
        type = click.STRING)
@click.option("-k",
        "--key",
        help = "subkey of the folder where results are stored within the indicated bucket. The data will be put at s3://bucket/{groupname}/key, where groupname comes from the registered dataset.",
        type = click.STRING)
@click.option("-l",
        "--localpath",
        help = "local path where config is located.",
        default = None,
        type = click.STRING)
@click.pass_obj
def register_resultpath(obj,bucket,key,localpath):        
    """Register a result path  with the scriptmanager. 

    """
    assert (bucket is not None and key is not None) ^ (localpath is not None), "you can pass either -b and -k (s3 file) or -l (local file)" 
    ## Get registration:
    path = obj["storage"]["path"]
    ncsm = NeuroCAASScriptManager.from_registration(path)
    if bucket is not None and key is not None:
        try:
            group = ncsm.get_group(ncsm.registration["data"])
        except KeyError:    
            raise AssertionError("data must be registered first.")
        path = os.path.join("s3://",bucket,group,key)
        ncsm.register_resultpath(path)
    elif localpath is not None:    
        ncsm.register_resultpath_local(localpath)


@workflow.command(help = "get a registered dataset from S3")
@click.option("-o",
        "--outputpath",
        help = "path to write output to.",
        default = None)
@click.option("-f",
        "--force",
        help = "if true, will redownload even if exists at intended output location",
        is_flag = True)
@click.option("-d",
        "--display",
        help = "if true, will show download progress",
        is_flag = True)
@click.pass_obj
def get_data(obj,outputpath,force,display):
    """Gets registered dataset from S3. 

    """
    path = obj["storage"]["path"]
    ncsm = NeuroCAASScriptManager.from_registration(path)
    kwargs = {}
    if outputpath is not None:
        kwargs["path"] = outputpath
    kwargs["force"] = force   
    kwargs["display"] = display   
    ncsm.get_data(**kwargs)

@workflow.command(help = "get a registered config from S3")
@click.option("-o",
        "--outputpath",
        help = "path to write output to.",
        default = None)
@click.option("-f",
        "--force",
        help = "if true, will redownload even if exists at intended output location",
        is_flag = True)
@click.option("-d",
        "--display",
        help = "if true, will show download progress",
        is_flag = True)
@click.pass_obj
def get_config(obj,outputpath,force,display):
    """Gets registered dataset from S3. 

    """
    path = obj["storage"]["path"]
    ncsm = NeuroCAASScriptManager.from_registration(path)
    kwargs = {}
    if outputpath is not None:
        kwargs["path"] = outputpath
    kwargs["force"] = force   
    kwargs["display"] = display   
    ncsm.get_config(**kwargs)

@workflow.command(help = "get a registered file from S3")
@click.option("-n",
        "--name",
        help = "name used to register this file.",
        )
@click.option("-o",
        "--outputpath",
        help = "path to write output to.",
        default = None)
@click.option("-f",
        "--force",
        help = "if true, will redownload even if exists at intended output location",
        is_flag = True)
@click.option("-d",
        "--display",
        help = "if true, will show download progress",
        is_flag = True)
@click.pass_obj
def get_file(obj,name,outputpath,force,display):
    """Gets registered dataset from S3. 

    """
    path = obj["storage"]["path"]
    ncsm = NeuroCAASScriptManager.from_registration(path)
    kwargs = {}
    kwargs["varname"] = name
    if outputpath is not None:
        kwargs["path"] = outputpath
    kwargs["force"] = force   
    kwargs["display"] = display   
    ncsm.get_file(**kwargs)

@workflow.command(help = "put a file into the result directory in s3")
@click.option("-r",
        "--resultpath",
        help = "local location of result file",
        default = None)
@click.option("-d",
        "--display",
        help = "if true, will show download progress",
        is_flag = True)
@click.pass_obj
def put_result(obj,resultpath,display):
    """puts a local file at the registered s3 location. 

    """
    path = obj["storage"]["path"]
    ncsm = NeuroCAASScriptManager.from_registration(path)
    kwargs = {}
    kwargs["localfile"] = resultpath
    kwargs["display"] = display   
    ncsm.put_result(**kwargs)

@workflow.command(help = "get the name of the dataset you registered")    
@click.pass_obj
def get_dataname(obj):
    """Gets the name of the dataset. 

    """
    path = obj["storage"]["path"]
    ncsm = NeuroCAASScriptManager.from_registration(path)
    dataname = ncsm.get_dataname()
    print(dataname)

@workflow.command(help = "get the name of the config file you registered")    
@click.pass_obj
def get_configname(obj):
    """Gets the name of the dataset. 

    """
    path = obj["storage"]["path"]
    ncsm = NeuroCAASScriptManager.from_registration(path)
    configname = ncsm.get_configname()
    print(configname)

@workflow.command(help = "get the name of the group whose data you are reading in. ")    
@click.pass_obj
def get_group(obj):
    """Gets the name of the group to whom the data belongs.. 

    """
    path = obj["storage"]["path"]
    ncsm = NeuroCAASScriptManager.from_registration(path)
    groupname = ncsm.get_group(ncsm.registration["data"])
    print(groupname)

@workflow.command(help = "get the name of the file you registered")    
@click.option("-n",
        "--name",
        help = "name of the file you registered.",
        type = click.STRING)
@click.pass_obj
def get_filename(obj,name):
    """Gets the name of the dataset. 

    """
    path = obj["storage"]["path"]
    ncsm = NeuroCAASScriptManager.from_registration(path)
    filename = ncsm.get_filename(name)
    print(filename)

@workflow.command(help = "get the path to the dataset you registered")    
@click.pass_obj
def get_datapath(obj):
    """Gets the path of the dataset. 

    """
    path = obj["storage"]["path"]
    ncsm = NeuroCAASScriptManager.from_registration(path)
    datapath = ncsm.get_datapath()
    print(datapath)

@workflow.command(help = "get the path to the config file you registered")    
@click.pass_obj
def get_configpath(obj):
    """Gets the path of the dataset. 

    """
    path = obj["storage"]["path"]
    ncsm = NeuroCAASScriptManager.from_registration(path)
    configpath = ncsm.get_configpath()
    print(configpath)

@workflow.command(help = "get the path to the file you registered")    
@click.option("-n",
        "--name",
        help = "name of the file you registered.",
        type = click.STRING)
@click.pass_obj
def get_filepath(obj,name):
    """Gets the path of the dataset. 

    """
    path = obj["storage"]["path"]
    ncsm = NeuroCAASScriptManager.from_registration(path)
    filepath = ncsm.get_filepath(name)
    print(filepath)

@workflow.command(help = "get the path to a temporary result location")
@click.pass_obj
def get_resultpath_tmp(obj):
    """Creates and returns name of temporary resultpath. 

    """
    path = obj["storage"]["path"]
    ncsm = NeuroCAASScriptManager.from_registration(path)
    print(ncsm.get_resultpath_tmp())



@workflow.command(help = "get the s3 path a local file or directory would be uploaded to")    
@click.option("-l",
        "--locpath",
        help = "path to file you want to get remote path for.",
        type = click.Path(exists = True,file_okay = True, dir_okay= True, resolve_path = True))
@click.pass_obj
def get_resultpath(obj,locpath):
    path = obj["storage"]["path"]
    ncsm = NeuroCAASScriptManager.from_registration(path)
    resultpath = ncsm.get_resultpath(locpath)
    print(resultpath)


@workflow.command(help = "runs a script with commands, but only locally.")
@click.option("-c",
        "--command",
        help = "the script (with arguments) you want to run.",
        type = click.STRING)
@click.pass_obj
def log_command_local(obj,command,suffix = None):    
    """Local version of log-command, shown below. Assumes that local resultpath is logged and taht it generates a process results folder., and will write a relevant logs directory within it.  

    UNTESTED, refactor into scripting module.

    """
    path = obj["storage"]["path"]
    ncsm = NeuroCAASScriptManager.from_registration(path)
    resultpath = os.path.join(os.path.dirname(os.path.dirname(ncsm.get_resultpath("/any_file/txt.txt"))),"logs")
    mkdir_notexists(resultpath)
    ncsm.log_command(command,"s3://nonexistent/file",resultpath) 

@workflow.command(help = "runs a script with commands, all specified as a string")
@click.option("-c",
        "--command",
        help = "the script (with arguments) you want to run.",
        type = click.STRING)
@click.option("-b",
        "--bucket",
        help = "bucket where results are located",
        type = click.STRING)
@click.option("-r",
        "--resultfolder",
        help = "path within the bucket to the results folder where we expect logs.",
        type = click.STRING)
@click.pass_obj
def log_command(obj,command,bucket,resultfolder,suffix = None):    
    """Assumes that in addition to a command to be run, we have a bucket and analysis folder where we can log results. 

    """
    path = obj["storage"]["path"]
    ncsm = NeuroCAASScriptManager.from_registration(path)
    groupname = ncsm.get_group(ncsm.registration["data"])
    try:
        dataname = os.path.basename(ncsm.get_dataname_remote())
    except AssertionError:    
        raise AssertionError("You must run register-dataset first so we know where to log this command.")

    if suffix is not None:
        logpath = os.path.join("s3://",bucket,groupname,resultfolder,"logs","DATASET_NAME:"+dataname+suffix+"_STATUS.txt")
    else:    
        logpath = os.path.join("s3://",bucket,groupname,resultfolder,"logs","DATASET_NAME:"+dataname+"_STATUS.txt")
    print("Attempting to log at {}".format(os.path.dirname(logpath)))    
        
    ncsm.log_command(command,logpath) 

@workflow.command(help = "takes care of post processing: sends end and config files to the bucket.")
@click.pass_obj
def cleanup(obj):
    path = obj["storage"]["path"]
    ncsm = NeuroCAASScriptManager.from_registration(path)
    ncsm.cleanup()
    
@cli.group(help = "develop remotely on an AWS instance.")
@click.pass_context
def remote(ctx):
    """remote functions.
    """
    from .remote import NeuroCAASAMI
    ctx.obj["remotemod"] = NeuroCAASAMI
    return 
    

### cli commands to manage a remote aws resources. 
## Initialize a new NeuroCAASAMI object, or get . 
@remote.command(help = "Initialize a NeuroCAASAMI object")
@click.option("-i",
        "--index",
        help = "if there are multiple development histories saved, index into them",
        default = -1
        )
@click.pass_obj
def develop_remote(blueprint,index):
    """Set up a NeuroCAASAMI object from the given analysis name and location. Checks to see if a NeuroCAASAMI object for this analysis already exists- if so, reloads from that object after asking user. Running this command saves the ami object to the NeuroCAAS config file, where it will be read by other methods.  

    """
    devhist = blueprint["blueprint"].blueprint_dict.get("develop_history",None)
    if devhist is not None: ## this whole condition is basically useless right now. 
        latest = devhist[index]
        instance = latest.get("instance_id",None)
        amis = latest.get("ami_hist",[])
        ami = []
        if len(amis) > 0:
            ami.append(ami[-1])
        # Ask the user if they want to work with an existing object or not. 
        initialize = click.confirm("This analysis has been developed before. Initialize with instance {} and ami {}?".format(instance,ami),default = False)
        if initialize:
            click.echo("Initializing from existing development history")
            ami = blueprint["remotemod"].from_dict(latest)
        else:    
            click.echo("Initializing from scratch")
            path = os.path.dirname(blueprint["blueprint"].config_filepath)
            ami = blueprint["remotemod"](path) 
    else:  
        click.echo("Initializing from scratch")
        path = os.path.dirname(blueprint["blueprint"].config_filepath)
        ami = blueprint["remotemod"](path) 
        blueprint["blueprint"].blueprint_dict["remote_hist"] = []
    ## write out to the remote_hist: 
    save_ami_to_cli(ami)
    


@remote.command(help = "Start developing remotely.")
@click.option("-f",
        "--force",
        help = "if true, will delete new instances even if they haven't been saved to amis",
        is_flag = True)
@click.pass_obj
def start_session(blueprint,force):
    """Essentially a new version of develop_remote above. Does away with the whole develop_history abstraction, and assumes that if you're starting a session the old session should be annihilated. 

    """
    ### Clear the details found in develop_dict
    try:
        dev_dict = blueprint["develop_dict"]
        assert dev_dict is not None
        deleted = delete_ami_from_cli(dev_dict,force)
        if deleted is False:
            click.echo("Did not delete previous session because instance has not been saved to ami (progress would be LOST). To force pass -f flag.")
            return 
    except (KeyError,AssertionError):    
        click.echo("Initializing from scratch")
    path = os.path.dirname(blueprint["blueprint"].config_filepath)
    ami = blueprint["remotemod"](path) 
    blueprint["blueprint"].blueprint_dict["remote_hist"] = []
    ## write out to the remote_hist: 
    save_ami_to_cli(ami)

@remote.command(help = "Finish development session.")
@click.option("-f",
        "--force",
        help = "if true, will delete new instances even if they haven't been saved to amis",
        is_flag = True)
@click.pass_obj
def end_session(blueprint,force):
    """Turns off development instances once you're done and clears development dictionary. 

    """
    try:
        dev_dict = blueprint["develop_dict"]
        assert dev_dict is not None
        deleted = delete_ami_from_cli(dev_dict,force)
        if deleted is False:
            click.echo("Did not delete previous session due to undeleted instances. To force pass -f flag.")
            return 
    except (KeyError,AssertionError):    
        click.echo("Nothing to delete.")


@remote.command(help = "Assign a new instance to a NeuroCAASAMI object")
@click.option("-i",
        "--instance",
        type = click.STRING,
        help = "instance id to assign to this instance. ")
@click.pass_obj
def assign_instance(blueprint,instance):    
    """Assign an existing instance from its instance ID to a blueprint["remotemod"] object so you can start developing on it. 

    """
    devdict = blueprint["develop_dict"]
    assert devdict is not None, "Development dict must exist. Run develop-remote"
    ami = blueprint["remotemod"].from_dict(devdict)
    ami.assign_instance(instance)
    save_ami_to_cli(ami)
        
@remote.command(help = "Launch a new instance from an ami")
@click.option("-a",
        "--amiid",
        type = click.STRING,
        help = "AMI id. ",
        default = None)
@click.option("-v",
        "--volumesize",
        type = click.INT,
        help = "size of the volume you want to attach to this instance.",
        default = None)
@click.option("-t",
        "--timeout",
        type = click.INT,
        help = "length of timeout to associate with this instance",
        default = 60)
@click.pass_obj
def launch_devinstance(blueprint,amiid,volumesize,timeout):
    """Launch a new instance. 

    """
    devdict = blueprint["develop_dict"]
    assert devdict is not None, "Development dict must exist. Run develop-remote"
    ami = blueprint["remotemod"].from_dict(devdict)
    ami.launch_devinstance(ami = amiid,volume_size = volumesize,timeout = timeout)
    save_ami_to_cli(ami)

@remote.command(help = "Start the current instance")
@click.option("-t",
        "--timeout",
        type = click.STRING,
        help = "length of timeout to associate with this instance",
        default = 60)
@click.pass_obj
def start_devinstance(blueprint,timeout):
    """Start an existing instance. 

    """
    devdict = blueprint["develop_dict"]
    assert devdict is not None, "Development dict must exist. Run develop-remote"
    ami = blueprint["remotemod"].from_dict(devdict)
    ami.start_devinstance(timeout = timeout)
    save_ami_to_cli(ami)

@remote.command(help = "Stop the current instance")
@click.pass_obj
def stop_devinstance(blueprint):
    """Stop an existing instance. 

    """
    devdict = blueprint["develop_dict"]
    assert devdict is not None, "Development dict must exist. Run develop-remote"
    ami = blueprint["remotemod"].from_dict(devdict)
    ami.stop_devinstance()
    save_ami_to_cli(ami)

@remote.command(help = "Terminate the current development instance")
@click.option("-f",
        "--force",
        type = click.BOOL,
        help = "whether or not to force deletion.",
        default = False)
@click.pass_obj
def terminate_devinstance(blueprint,force):
    """Terminate an existing instance. 

    """
    devdict = blueprint["develop_dict"]
    assert devdict is not None, "Development dict must exist. Run develop-remote"
    ami = blueprint["remotemod"].from_dict(devdict)
    ami.terminate_devinstance(force = force)
    save_ami_to_cli(ami)

@remote.command(help = "Get the ip address of the instance.")
@click.pass_obj
def get_ip(blueprint):
    """Get ip address of an instance.  

    """
    devdict = blueprint["develop_dict"]
    assert devdict is not None, "Development dict must exist. Run develop-remote"
    ami = blueprint["remotemod"].from_dict(devdict)
    ami.instance.reload()
    ami.ip = ami.instance.public_ip_address
    click.echo(ami.ip)

@remote.command(help = "Get the lifetime of the instance")
@click.pass_obj
def get_lifetime(blueprint):
    """Get the lifetime remaining on an active instance.  

    """
    devdict = blueprint["develop_dict"]
    assert devdict is not None, "Development dict must exist. Run develop-remote"
    ami = blueprint["remotemod"].from_dict(devdict)
    click.echo(ami.get_lifetime())

@remote.command(help = "Get the lifetime of the instance")
@click.option("-m",
        "--minutes",
        help = "number of minutes to extend lifetime by.",
        type = click.INT,
        )
@click.pass_obj
def extend_lifetime(blueprint,minutes):
    """Extend the lifetime off an active instance. 

    """
    devdict = blueprint["develop_dict"]
    assert devdict is not None, "Development dict must exist. Run develop-remote"
    ami = blueprint["remotemod"].from_dict(devdict)
    ami.extend_lifetime(minutes)

@remote.command(help = "submit a job to your instance. Optionally, you can upload datasets and config files to s3 if you will be referencing them in your submitpath for a faster turnaround.")
@click.option("-s",
        "--submitpath",
        help = "path to submitfile",
        type = click.Path(exists = True,file_okay = True,dir_okay = True,readable = True,resolve_path = True),
        )
@click.option("-d",
        "--data",
        help = "path to test dataset.",
        type = click.Path(exists = True,file_okay = True,dir_okay = True,readable = True,resolve_path = True),
        multiple = True,
        default = None)
@click.option("-c",
        "--config",
        help = "path to test config file.",
        type = click.Path(exists = True,file_okay = True,dir_okay = True,readable = True,resolve_path = True),
        multiple = True,
        default = None)
@click.pass_obj
def submit_job(blueprint,submitpath,data,config):
    """Submit a job to the instance you're developing on. 

    """
    #for dat in data:
    #    
    #    datname = os.path.basename(dat)
    #    shutil.copyfile(dat,os.path.join(analysis_location,"io-dir","inputs",datname))

    ### Deposit all configs into the config directory:
    #for conf in config:
    #    confname = os.path.basename(conf)
    #    shutil.copyfile(conf,os.path.join(analysis_location,"io-dir","configs",confname))
    devdict = blueprint["develop_dict"]
    assert devdict is not None, "Development dict must exist. Run develop-remote"
    ami = blueprint["remotemod"].from_dict(devdict)
    ami.submit_job(submitpath)
    save_ami_to_cli(ami)

@remote.command(help = "get the status from the most recently run job.")
@click.option("-j",
        "--jobind",
        help = "index of job to get the output for",
        type = click.INT,
        default = -1)
@click.pass_obj
def job_status(blueprint,jobind):    
    """Read stdout and stderr from the instance you're developing on.  

    """
    devdict = blueprint["develop_dict"]
    assert devdict is not None, "Development dict must exist. Run develop-remote"
    ami = blueprint["remotemod"].from_dict(devdict)
    ami.job_status(jobind)
    save_ami_to_cli(ami)

@remote.command(help = "get the output from the most recently run job.")
@click.option("-j",
        "--jobind",
        help = "index of job to get the output for",
        type = click.INT,
        default = -1)
@click.pass_obj
def job_output(blueprint,jobind):    
    """Read stdout and stderr from the instance you're developing on.  

    """
    devdict = blueprint["develop_dict"]
    assert devdict is not None, "Development dict must exist. Run develop-remote"
    ami = blueprint["remotemod"].from_dict(devdict)
    ami.job_output(jobind)
    save_ami_to_cli(ami)

@remote.command(help = "save the current development instance into an ami.")
@click.option("-n",
        "--name",
        help = "name to give to the new ami",
        type = click.STRING,
        )
@click.pass_obj
def create_devami(blueprint,name):    
    """Save the image of the instance you're developing on.   

    """
    devdict = blueprint["develop_dict"]
    assert devdict is not None, "Development dict must exist. Run develop-remote"
    ami = blueprint["remotemod"].from_dict(devdict)
    ami.create_devami(name)
    save_ami_to_cli(ami)

@remote.command(help = "update the blueprint with most recently developed amis.")
@click.option("-a",
        "--amiid",
        help = "id of new ami (will default to newest in list if not given)",
        type = click.STRING,
        default = None
        )
@click.option("-m",
        "--message",
        help = "message associated with the commit carried out with this command.",
        type = click.STRING,
        default = None
        )
@click.pass_obj
def update_blueprint(blueprint,amiid,message):    
    """Update the blueprint of the instance you're developing on.   

    """
    devdict = blueprint["develop_dict"]
    assert devdict is not None, "Development dict must exist. Run develop-remote"
    ami = blueprint["remotemod"].from_dict(devdict)
    ami.update_blueprint(amiid,message)
    save_ami_to_cli(ami)

#@remote.command(help = "save to development history")
#@click.pass_obj
#def update_history(blueprint):
#    """Add this ami's current state to development history. 
#
#    """
#    devdict = blueprint["develop_dict"]
#    assert devdict is not None, "Development dict must exist. Run develop-remote"
#    ami = NeuroCAASAMI.from_dict(devdict)
#    blueprint["blueprint"].blueprint_dict["develop_history"].append(ami.to_dict())
