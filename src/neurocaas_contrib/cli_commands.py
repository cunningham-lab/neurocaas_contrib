## Mimicking cli structure given in remote-docker-aws repository. 
import subprocess
import sys
import shutil
import click 
import json
import os
from .blueprint import Blueprint
from .local import NeuroCAASImage,NeuroCAASLocalEnv
from .scripting import get_yaml_field,parse_zipfile,NeuroCAASScriptManager

## template location settings:
dir_loc = os.path.abspath(os.path.dirname(__file__))
template_dir= os.path.join(dir_loc,"template_mats") 
default_write_loc = os.path.join(dir_loc,"local_envs")

if "pytest" in sys.modules:
    mode = "test"
else:
    mode = "std"

if mode == "test":
    configname = ".neurocaas_contrib_config_test.json"
    configpath = os.path.join(".",configname)
    ## "separate for data storage during actual runs"
    storagename = ".neurocaas_contrib_storageloc_test.json" 
    storagepath = os.path.join(".",storagename)

else:    
    ## configuration file settings:
    configname = ".neurocaas_contrib_config.json"
    configpath = os.path.join(os.path.expanduser("~"),configname)
    storagename = ".neurocaas_contrib_storageloc.json" 
    storagepath = os.path.join(os.path.expanduser("~"),storagename)


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
    if ctx.invoked_subcommand in no_blueprint:
        return ## move on and run configure. 
    else:
        if location is None or analysis_name is None:
            try:
                with open(configpath,"r") as f:
                    defaultconfig = json.load(f)
            except FileNotFoundError:    
                raise click.ClickException("Configuration file not found. Run `neurocaas_contrib init` to initialize the cli.")
            if location is None:
                location = defaultconfig["location"]
            if analysis_name is None:    
                analysis_name = defaultconfig["analysis_name"]

        ctx.obj = {}
        ctx.obj["location"] = location
        ctx.obj["analysis_name"] = analysis_name
        try:
            ctx.obj["blueprint"] = Blueprint(os.path.join(location,analysis_name,"stack_config_template.json")) ## we can now reference the context object with the decorator pass_obj, as below. 
        except FileNotFoundError as e:
            raise click.ClickException("Blueprint for analysis {} not found in location {}. Run `neurocaas_contrib init` first".format(ctx.obj["analysis_name"],ctx.obj["location"]))

@cli.command(help ="configure CLI to work with certain analysis.")
@click.option(
    "--location",
    help="Directory where we should store materials to develop this analysis. By default, this is: \n\b\n{}".format(default_write_loc), 
    default=default_write_loc
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
            shutil.copyfile(template_blueprint,os.path.join(analysis_location,"stack_config_template.json"))
        else:    
            print("Not creating analysis folder at this location.")
    elif not os.path.exists(os.path.join(analysis_location,"stack_config_template.json")):    
        initialize = click.confirm("The analysis named {} at {} is not correctly initialized. Initialize?".format(analysis_name,location),default = False)
        if initialize:
            ###Setup happens here
            template_blueprint = os.path.join(template_dir,"stack_config_template.json")
            shutil.copyfile(template_blueprint,os.path.join(analysis_location,"stack_config_template.json"))
        else:    
            print("Not creating analysis folder at this location.")
    else:        
        create = True
        initialize = True

    ## Only if you created or initialized an analysis folder should the config file be written to.
    if create or initialize:
        ## First set the analysis name in the config file:
        analysis_settings = {"analysis_name":analysis_name,
                             "location":location
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
    default=default_write_loc,
    type = click.Path(exists = True,file_okay = False,dir_okay = True,readable = True,resolve_path = True)
        )
def describe_analyses(location):
    """List all of the analyses available to develop on. Takes a location parameter: by default will be the packaged local_envs location. 

    """
    all_contents = os.listdir(location) 
    dirs = [ac for ac in all_contents if os.path.isdir(os.path.join(location,ac))] 
    ## Add a star for the current one. 
    try:
        with open(configpath,"r") as f:
            config = json.load(f)
        currentanalysis = config["analysis_name"]    
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
@scripting.command(help = "extract field from a yaml file as a string.")
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
    try:
        dataname = ncsm.get_dataname()
    except AssertionError:    
        raise AssertionError("You must run get-data first so we know where to log this command.")

    if suffix is not None:
        logpath = os.path.join("s3://",bucket,resultfolder,"logs","DATASET_NAME:"+dataname+suffix+"_STATUS.txt")
    else:    
        logpath = os.path.join("s3://",bucket,resultfolder,"logs","DATASET_NAME:"+dataname+"_STATUS.txt")
        
    ncsm.log_command(command,logpath) 

@workflow.command(help = "takes care of post processing: sends end and config files to the bucket.")
@click.pass_obj
def cleanup(obj):
    path = obj["storage"]["path"]
    ncsm = NeuroCAASScriptManager.from_registration(path)
    ncsm.cleanup()
