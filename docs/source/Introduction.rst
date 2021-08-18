Introduction
============

This repository contains a command line tool to assist developers in the process of building and deploying their analyses to NeuroCAAS. 

The main CLI command, :code:`neurocaas-contrib`, has a bunch of subcommands which become useful in various parts of the development process. Highlighting a few important ones:

- To get started, :code:`neurocaas-contrib workflow` contains tools to manage data transfer between cloud storage and the machine where the command is run, making it useful to handle data transfer inside into analysis processing scripts.
- Then, you can use :code:`neurocaas-contrib remote` to start up and manage an AWS instance, and set up your code to work on that instance.
- Once you have working analysis, you can use :code:`neurocaas-contrib monitor` to monitor how users are accessing analyses that you built.
 
The rest of this page contains detailed API documentation for the neurocaas-contrib CLI tool. For a full developer guide, checkout the NeuroCAAS source repository `here <https://github.com/cunningham-lab/neurocaas>`_.
