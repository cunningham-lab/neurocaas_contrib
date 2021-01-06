## Mimicking cli structure given in remote-docker-aws repository. 
import shutil
import click 
import json
import os
from .blueprint import Blueprint
from .local import NeuroCAASImage

dir_loc = os.path.abspath(os.path.dirname(__file__))
template_dir= os.path.join(dir_loc,"local_envs","templatestack") 

@click.group()
@click.option(
    "--location",
    help="Root location for neurocaas local environment build.", 
    default=os.path.join(dir_loc,"local_envs")
        )
@click.option(
    "-a",   
    "--analysis_name",
    help="Root location for neurocaas local environment build.", 
    )
@click.pass_context
def cli(ctx,location,analysis_name):
    click.echo()
    ctx.obj = {}
    ctx.obj["location"] = location
    ctx.obj["analysis_name"] = analysis_name
    ctx.obj["active_image"] = NeuroCAASImage()
    try:
        ctx.obj["blueprint"] = Blueprint(os.path.join(location,analysis_name,"stack_config_template.json")) ## we can now reference the context object with the decorator pass_obj, as below. 
    except TypeError as e:
        print(e)

@cli.command()
@click.option(
    "--analysis-name",
    help="Name of the analysis you want to work on." 
        )
@click.pass_obj
def configure(blueprint,analysis_name):
    """Sets up the command line utility to work with a certain analysis by default. If analysis folder does not yet exist, creates it. 
    """
    blueprint["analysis_name"] = analysis_name
    analysis_location = os.path.join(blueprint["location"],analysis_name)
    print(blueprint,"blueprint")
    if not os.path.exists(analysis_location):
        os.mkdir(analysis_location) 
    ###Setup happens here
    template_blueprint = os.path.join(template_dir,"stack_config_template.json")
    shutil.copyfile(template_blueprint,os.path.join(analysis_location,"stack_config_template.json"))

    ###
    #blueprint["blueprint"] = Blueprint(os.path.join(analysis_location,"stack_config_template.json")) ## we can now reference the context object with the decorator pass_obj, as below. 

@cli.command(help = "print the current blueprint.")
@click.pass_obj
def get_blueprint(blueprint):
    string = json.dumps(blueprint["blueprint"].blueprint_dict,indent = 2)
    click.echo(string)

@cli.command(help = "setup a containerized environment to start developing.")
@click.pass_obj
def setup_image(blueprint):
    blueprint["active_image"].setup_container()
    blueprint["blueprint"].blueprint_dict["active_container"] = blueprint["active_image"].container_name
    blueprint["blueprint"].blueprint_dict["active_image"] = blueprint["active_image"].image_tag 
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
@click.pass_obj
def save_developed_image(blueprint,tagid,force):
    try:
        image = blueprint["active_image"]
    except KeyError:
        click.echo("Image not found. Run `setup_image` first.")
        raise
    tag = "{}.{}".format(blueprint["analysis_name"],tagid)
    image.save_container_to_image(tag,force)








