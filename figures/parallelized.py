## script to calculate what proportion of usage is parallelized. 
import logging
import numpy as np
import datetime
from neurocaas_contrib.monitor import RangeFinder
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import json 
import os
import sys

mpl.rcParams["axes.titlesize"] = "large" 
mpl.rcParams["axes.labelsize"] = "large"

mpl.rcParams["xtick.labelsize"] = "large"
mpl.rcParams["ytick.labelsize"] = "large"

logging.basicConfig(level = logging.WARNING)

"""This script takes the output of a neurocaas_contrib calculate-parallelism run, and makes a histogram out of it. It takes a path to a directory, and will then take all of the parallel_logs json files within as its source material. At the moment, this includes the following analyses:  
    - epi-ncap-web
    - dlc-ncap-web
    - pmd-ncap-web
    - caiman-ncap-web
    - locanmf-ncap-web
    - bardensr
    - dlc-ncap-stable
    - caiman-ncap-stable
    - polleuxmonitored
    - carceamonitored
    - wfield-preprocess
    - yass-ncap-stable
    - one-photon-compress
    - one-photon-demix
    - one-photon-mcorr
    - dgp-refactor
    - ensemble-dgp
    - label-job-create-web

:param path: the path to the directory.

"""

## parallelism params
#bins = [1,2,5,17,65,64*4+1]
base = 2
power = 8
bins = [base**i for i in range(8)]
## user params
userbins = [base**i for i in range(10)]
userbins_duration = [base**(i-3) for i in range(10)]
userbins = [0] + userbins 
userbins_duration = [0] + userbins_duration 
sum_intervals = [[bins[i],bins[i+1]] for i in range(len(bins)-1)]
## data params
analyses = {
        "epi-ncap-web":{"dev":"internal","name":"Emergent Property Inference (public)"},
        "dlc-ncap-web":{"dev":"internal","name":"DeepLabCut (public)"}, 
        "pmd-ncap-web":{"dev":"internal","name":"PMD (public)"}, 
        "caiman-ncap-web":{"dev":"internal","name":"CaImAn (public)"}, 
        "locanmf-ncap-web":{"dev":"internal","name":"LocaNMF (public)"}, 
        "bardensr":{"dev":"external","name":"Bardensr (public)"}, 
        "dlc-ncap-stable":{"dev":"internal","name":"DeepLabCut (dev)"}, 
        "caiman-ncap-stable":{"dev":"internal","name":"CaImAn (dev)"}, 
        "polleuxmonitored":{"dev":"custom","name":"DLC Tracking (Polleux)"}, 
        "carceamonitored":{"dev":"custom","name":"DLC Tracking (Carcea)"}, 
        "wfield-preprocess":{"dev":"native","name":"WFCI (public)"}, 
        "yass-ncap-stable":{"dev":"internal","name":"YASS (public)"}, 
        "one-photon-compress":{"dev":"internal","name":"1p compression (dev)"}, 
        "one-photon-demix":{"dev":"internal","name":"1p demixing (dev)"}, 
        "one-photon-mcorr":{"dev":"internal","name":"1p motion correction (dev)"}, 
        "dgp-refactor":{"dev":"internal","name":"DeepGraphPose (public)"}, 
        "ensemble-dgp":{"dev":"native","name":"Ensemble DeepGraphPose (public)"}, 
        "label-job-create-web":{"dev":"external","name":"Labeling GUI (public)"}, 
    }
analysiscolors = {"internal":"#1f78b4","external":"#b2df8a","custom":"#a6cee3","native":"#33a02c"}

def get_logs(path):
    """Get names of all log files:

    :path: path to directory where we have log files. 
    """
    assert path is not None, "you must provide a valid path where log info is stored."
    logfile_cands = os.listdir(path)
    logfiles = [lc for lc in logfile_cands if lc.endswith("parallel_logs.json")]

    return logfiles

def process_log_files(path,logfiles):
    """Iterate through json logs, and extract useful information. Exclude datapoint we do not trust. 

    :param path: path to the directory where log files are located.  
    :param logfiles: all the names of the log files.
    :returns: all_parallelism,all_duration,count: the number of jobs sorted by parallelism, the duration of jobs sorted by parallelism, and the number of jobs that were longer than 50 seconds. 
    """
    ## Initialize var types.
    all_parallelism = []
    all_durations = {} 
    all_users = {}
    all_user_durations = {}
    all_data = {}
    all_data_durations = {}
    count = 0

    ## Iterate through all log files.
    for logfile in logfiles:
        logging.info(os.path.join(path,logfile))
        try:
            with open(os.path.join(path,logfile)) as f:
                loginfo = json.load(f)
        except json.decoder.JSONDecodeError:        
            continue
        for job in loginfo.values():
            ## filter out internal testing and some problem files. 
            print(job["instances"][0]["jobpath"])
            if job["instances"][0]["jobpath"].startswith("reviewers"):
                continue
            if job["instances"][0]["jobpath"].startswith("debuggers"):
                continue
            if job["instances"][0]["jobpath"].startswith("examplegroup2"):
                continue
            if job["instances"][0]["jobpath"] in ["sawtelllab/results/job__dlc-ncap-web_1595302867","sawtelllabdlcdevelop/results/job__dlc-ncap-stable_20200720_16_47"]: 
                continue ## These are breaking bugs that also influence graph interpretation, exclude.
            if job["instances"][0]["databucket"] == "cianalysispermastack":
                continue

            ## Get user names: 
            datapath = job["instances"][0]["datapath"]
            if type(datapath) is list:
                datapath = datapath[0]
                
            username = datapath.split("/")[0]
            bucketname = job["instances"][0]["databucket"]

            all_parallelism.append(len(job["instances"]))
            ## Per job we only need one startdate.
            rf.update(job["instances"][0]["start"])

            for di,dur in job["durations"].items():
                try:
                    if dur < 0:
                        job["durations"][di] = 0
                        print("negative time detected: setting duration to zero")
                except TypeError:       
                    job["durations"][di] = 0
                    print("none time: setting duration to zero")
            job_duration = sum(job["durations"].values())



            try:
                all_durations[len(job["durations"])]+=job_duration
            except KeyError:    
                all_durations[len(job["durations"])] =job_duration
            try: 
                all_users[username] += len(job["instances"])
                all_user_durations[username] += job_duration
            except: 
                all_users[username] = len(job["instances"])
                all_user_durations[username] = job_duration 
            try:    
                all_data[bucketname] += len(job["instances"])
                all_data_durations[bucketname] += job_duration
            except:    
                all_data[bucketname] = len(job["instances"])
                all_data_durations[bucketname] = job_duration

            if len(job["durations"]) > 50:   
                logging.warning(json.dumps(job["instances"][0],indent = 4))
                count += 1
    return all_parallelism, all_durations, all_users, all_user_durations, all_data, all_data_durations, count        

#sum_intervals = [[0,1],[2,4],[5,16],[17,64],[64,80]]
if __name__ == "__main__":
    ## Find all log files. 
    rf = RangeFinder()
    path = sys.argv[1]
    logfiles = get_logs(path)
    
    ## get out the parallelism and duration data from log files: 
    all_parallelism,all_durations, all_users, all_user_durations, all_data, all_data_durations ,count = process_log_files(path,logfiles)

    ## Format durations
    duration_keys = list(all_durations.keys())
    duration_values = [all_durations[v]/3600 for v in duration_keys]
    duration_array = np.zeros(90,)    
    for dk in duration_keys:
        duration_array[dk] = all_durations[dk]/3600
    values_binned = [sum(duration_array[interval[0]:interval[1]+1]) for interval in sum_intervals]    
    logging.info(count) ## nb jobs greater than 1
    startdate,enddate = rf.range_months()
    logging.info(str(startdate)+" "+str(enddate))

    ## Generate plot
    fig,ax = plt.subplots(2,1,sharex = False,figsize = (7,5))
    ax[0].hist(all_parallelism,bins = bins,log = True,edgecolor = "black")
    ax[0].set_ylabel("Total Job Count")
    ax[0].set_xscale("log",base = base)
    ax[0].tick_params(
    axis='x',          # changes apply to the x-axis
    which='both',      # both major and minor ticks are affected
    labelbottom=False,
    bottom = False) # labels along the bottom edge are off
    #ax[1].bar(duration_keys,duration_values)
    #ax[1].bar([i for i in range(len(values_binned))],values_binned)
    ax[1].bar(bins[:-1],values_binned,width = np.diff(bins),log = True,ec = "k",align = "edge")
    ax[1].set_yscale('log')
    ax[1].set_xscale('log',base = base)
    ax[1].set_xlabel("Number of datasets per job")
    ax[1].set_ylabel("Total Compute Hours")
    ax[0].set_title("Job size statistics for NeuroCAAS web service,\n {} to {}".format(startdate,enddate),fontsize =20)

    plt.tight_layout()
    now = str(datetime.datetime.now())

    plt.savefig(os.path.join(path,f"parallelism_figure_{now}.pdf"))
    plt.close()

    ## Format user durations
    user_values = list(all_users.values())
    duration_values = [vi/3600 for vi in all_user_durations.values()]

    fig,ax = plt.subplots(1,2,figsize = (10,5),sharex = False)
    fig.canvas.draw()
    ax[0].hist(np.clip(user_values,userbins[0],userbins[-1]),bins = userbins,log= False,edgecolor = "black")
    ax[0].set_xscale("log",base = base)
    #ax[0].tick_params(
    #axis='x',          # changes apply to the x-axis
    #which='both',      # both major and minor ticks are affected
    #labelbottom=False,
    #bottom = False) # labels along the bottom edge are off
    ax[0].set_ylabel("Number of Users")
    ax[0].set_xlabel("Number of Datasets")
    ax[1].hist(np.clip(duration_values,userbins_duration[0],userbins_duration[-1]),bins = userbins_duration,log= False,edgecolor = "black")
    ax[1].set_xscale("log",base = base)
    ax[1].annotate("+",(-1,2))
    #xticklabels = ax[1].get_xticklabels()
    #final = ax[1].yaxis.get_major_ticks()[-1].label
    #durlabels = [item._text for item in ax[1].get_xticklabels()]
    ##durlabels[-1] = durlabels[-1]+"+"
    #print(durlabels)
    #ax[1].set_xticklabels(durlabels)


    #xticklabels[-1] = xticklabels[-1].get_text()+"+"

    ##labs = ["$2^{"+str(int(max(np.log2(i),0)))+"}$" for ii,i in enumerate(userbins) if ii%2 == 2]
    ##labs[-1] = ">"+labs[-1] 
    ##labs_dur = ["$2^{"+str(int(max(np.log2(i),0)))+"}$" for ii,i in enumerate(userbins_duration) if ii%2 == 2]
    ##labs_dur[-1] = ">"+labs_dur[-1] 
    ##labs = [0,0]+labs
    ##labs_dur = [0,0]+labs_dur
    ##ax[0].set_xticklabels(labs)
    ##ax[1].set_xticklabels(labs_dur)


    #ax[1].tick_params(
    #axis='x',          # changes apply to the x-axis
    #which='both',      # both major and minor ticks are affected
    #labelbottom=False,
    #bottom = False) # labels along the bottom edge are off
    ax[1].set_ylabel("Number of Users")
    ax[1].set_xlabel("Number of Hours")
    plt.suptitle("User statistics for NeuroCAAS web service,\n {} to {}".format(startdate,enddate),fontsize = 20,y=1.001)
    plt.savefig(os.path.join(path,f"user_figure{now}.pdf"))
    plt.tight_layout()
    plt.close()

    fig,ax = plt.subplots(2,1,figsize = (10,10))
    datasets = all_data.keys()

    sorted_all_data = {k:v for k,v in sorted(all_data.items(),key = lambda item:item[1])}
    sorted_all_data_durations = {k:v for k,v in sorted(all_data_durations.items(),key = lambda item:item[1])}
    custom_lines = [Line2D([0],[0],color = analysiscolors["internal"],lw=4),
                    Line2D([0],[0],color = analysiscolors["external"],lw=4),
                    Line2D([0],[0],color = analysiscolors["native"],lw=4),
                    Line2D([0],[0],color = analysiscolors["custom"],lw=4)]
    ax[0].legend(custom_lines,["Internal","External","Native","Custom"])


    ax[0].barh(range(len(datasets)),sorted_all_data.values(),log = True,color = [analysiscolors[analyses[f]["dev"]] for f in sorted_all_data.keys()])
    ax[0].set_yticks(range(len(datasets)),labels=[analyses[sk]["name"] for sk in sorted_all_data.keys()],rotation = 30)
    ax[0].set_xlabel("Number of Datasets")
    ax[1].barh(range(len(datasets)),np.array(list(sorted_all_data_durations.values()))/3600,log = True,color = [analysiscolors[analyses[f]["dev"]] for f in sorted_all_data_durations.keys()])
    ax[1].set_yticks(range(len(datasets)),labels=[analyses[sk]["name"] for sk in sorted_all_data_durations.keys()],rotation = 30)
    ax[1].set_xlabel("Number of Hours")
    ax[0].set_title("Per analysis statistics for NeuroCAAS web service,\n {} to {}".format(startdate,enddate),fontsize=20)
    plt.tight_layout()
    plt.savefig(os.path.join(path,f"data_figure{now}.pdf"))
    plt.close()


    


