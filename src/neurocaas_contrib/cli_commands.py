## Mimicking cli structure given in remote-docker-aws repository. 
import click 
import json
import os
from .blueprint import Blueprint

@click.group()
@click.option(
    "--analysis-name",
    help="Name of the analysis you want to work on." 
        )
@click.pass_context
def cli(ctx,analysis_name):
    click.echo(analysis_name)
    ctx.obj = Blueprint(analysis_name) ## we can now reference the context object with the decorator pass_obj, as below. 

@cli.command()
@click.pass_obj
def get_blueprint(blueprint):
    click.echo("here")
    string = json.dumps(blueprint.blueprint_dict,indent = 2)
    click.echo(string)

# configure (create new directory)

# status (see current status)

# setup
