# NeuroCAAS Remote
## A repository to assist the creation of new pipelines on the NeuroCAAS platform. 

This repository contains scripts that coordinate analyses that we built and host on NeuroCAAS. It serves to provide transparency for the analyses that we provide (all analysis code for NeuroCAAS is contained in this repo or the original analysis repo), and as a template for developers who would like to offer their analyses on NeuroCAAS. For these developers, this repo houses a collection of utilities that automate the process of coordinating logs and system monitoring with the NeuroCAAS platform and the web frontend. 

To get started, the script "run_main.sh" runs all of the setup and cleanup required by NeuroCAAS, as well as declaring useful variables to streamline data transfer and directory navigation. Take a look at how it calls analysis-specific scripts within it, and consider how that can be adapted for your pipeline. See the epi, dlc, caiman, locanmf, and pmd subfolders to see how other analyses function within this framework. 


