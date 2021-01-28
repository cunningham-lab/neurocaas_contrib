## Mimicking cli structure given in remote-docker-aws repository. 
import subprocess
import sys
import shutil
import click 
import json
import os
from .blueprint import Blueprint
from .local import NeuroCAASImage,NeuroCAASLocalEnv

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

else:    
    ## configuration file settings:
    configname = ".neurocaas_contrib_config.json"
    configpath = os.path.join(os.path.expanduser("~"),configname)


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
    no_blueprint = ['init','describe-analyses']
    if ctx.invoked_subcommand in no_blueprint:
        return ## move on and run configure. 
    else:
        if location is None or analysis_name is None:
            try:
                with open(configpath,"r") as f:
                    defaultconfig = json.load(f)
            except FileNotFoundError:    
                raise click.ClickException("Configuration file not found. Run `neurocaas_contrib configure` to initialize the cli.")
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

@cli.command(help = "print information about the IAE from the blueprint.")
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
@cli.command(help = "set up an environment to develop in.")
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

@cli.command(help = "removes the current active container.")
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

@cli.command(help = "save a container to a new image.")
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

@cli.command(help="enter the container to start development.")
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

@cli.command(help = "prepare sample input data.")
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
@cli.command(help = "run analysis in a saved environment.")
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








