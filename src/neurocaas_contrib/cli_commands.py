## Mimicking cli structure given in remote-docker-aws repository. 
import sys
import shutil
import click 
import json
import os
from .blueprint import Blueprint
from .local import NeuroCAASImage

## template location settings:
dir_loc = os.path.abspath(os.path.dirname(__file__))
template_dir= os.path.join(dir_loc,"local_envs","templatestack") 

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
    """ Base command to interact with the neurocaas_contrib repo from the command line. Can be given location and analysis name parameters to run certain actions in a one-off manner, but preferred workflow is assigning these with the `configure` subcommand. Assigns parameters (analysis metadata, blueprint, active image) to be referenced in other subparameters.  

    """
    if ctx.invoked_subcommand == 'init':
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

@cli.command()
@click.option(
    "--location",
    help="Root location for neurocaas local environment build.", 
    default=os.path.join(dir_loc,"local_envs")
        )
@click.option(
    "--analysis-name",
    help="Name of the analysis you want to work on." ,
    prompt = True
        )
@click.pass_obj
def init(blueprint,location,analysis_name):
    """Sets up the command line utility to work with a certain analysis by default. Must be run on first usage of the cli, and run to create new analysis folders in given locations. If analysis folder does not yet exist, creates it.  
    """
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

    #if analysis_name is None:
    #    analysis_name = blueprint["analysis_name"]
    analysis_location = os.path.join(location,analysis_name)

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

@cli.command(help = "print the current blueprint.")
@click.pass_obj
def get_blueprint(blueprint):
    string = json.dumps(blueprint["blueprint"].blueprint_dict,indent = 2)
    click.echo(string)

@click.option("-i",
        "--image",
        help = "base image tag to use as the start of development. If not given, reverts to entry in blueprint.",
        default = None)
@click.option("-c",
        "--container",
        help = "name to give to containers",
        default="neurocaasdevcontainer")
@cli.command(help = "setup a containerized environment to start developing.")
@click.pass_obj
def setup_development_container(blueprint,image,container):
    """Launches a container from an image of your choice so that you can perform configuration."""
    ## See if the blueprint has the fields you want:
    if image is None:
        image = blueprint["blueprint"].blueprint_dict.get("active_image",None)
    active_image = NeuroCAASImage(image,container)
    active_image.setup_container()
    blueprint["blueprint"].blueprint_dict["active_container"] = active_image.container_name
    blueprint["blueprint"].blueprint_dict["active_image"] = active_image.image_tag 
    blueprint["blueprint"].write()

### TODO delete image. 

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
@click.pass_obj
def save_developed_image(blueprint,tagid,force,container):
    """Saves a container into a new image, and saves that image as the new default for this analysis. """
    try:
        container_name = blueprint["blueprint"].blueprint_dict.get("active_container",None)
        image = NeuroCAASImage(None,None) 
        image.assign_default_container(container_name)
    except KeyError:
        click.echo("Image not found. Run `setup_image` first.")
        raise
    tag = "{}.{}".format(blueprint["analysis_name"],tagid)
    saved = image.save_container_to_image(tag,force)
    if saved:
        blueprint["blueprint"].blueprint_dict["active_image"] = "{}:{}".format(image.repo_name,tag) 
        blueprint["blueprint"].write()
        image.current_container.stop()








