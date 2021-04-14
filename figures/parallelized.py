## script to calculate what proportion of usage is parallelized. 
import logging
import numpy as np
import datetime
from neurocaas_contrib.monitor import RangeFinder
import matplotlib.pyplot as plt
import json 
import os
import sys

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
    - dlc-ncap-demo
    - carceamonitored

:param path: the path to the directory.

"""

#bins = [1,2,5,17,65,64*4+1]
base = 2
power = 8
bins = [base**i for i in range(8)]
sum_intervals = [[bins[i],bins[i+1]] for i in range(len(bins)-1)]

#sum_intervals = [[0,1],[2,4],[5,16],[17,64],[64,80]]
if __name__ == "__main__":
    rf = RangeFinder()
    path = sys.argv[1]
    assert path is not None, "you must provide a valid path where log info is stored."
    logfile_cands = os.listdir(path)
    logfiles = [lc for lc in logfile_cands if lc.endswith("parallel_logs.json")]
    
    all_parallelism = []
    all_durations = {} 
    count = 0
    for logfile in logfiles:
        logging.info(os.path.join(path,logfile))
        try:
            with open(os.path.join(path,logfile)) as f:
                loginfo = json.load(f)
        except json.decoder.JSONDecodeError:        
            continue
        for job in loginfo.values():
            print(job["instances"][0]["jobpath"])
            if job["instances"][0]["jobpath"].startswith("reviewers"):
                continue
            if job["instances"][0]["jobpath"].startswith("debuggers"):
                continue
            if job["instances"][0]["jobpath"].startswith("examplegroup2"):
                continue
            if job["instances"][0]["jobpath"] in ["sawtelllab/results/job__dlc-ncap-web_1595302867","sawtelllabdlcdevelop/results/job__dlc-ncap-stable_20200720_16_47"]: 
                continue ## These are breaking bugs that also influence graph interpretation, exclude.
            all_parallelism.append(len(job["instances"]))
            ## Per job we only need one startdate.
            rf.update(job["instances"][0]["start"])
            try:
                all_durations[len(job["durations"])]+=sum(job["durations"].values())
            except KeyError:    
                all_durations[len(job["durations"])] =sum(job["durations"].values())
            if len(job["durations"]) > 50:   
                logging.warning(json.dumps(job["instances"][0],indent = 4))
                count += 1
    duration_keys = list(all_durations.keys())
    duration_values = [all_durations[v]/3600 for v in duration_keys]
    duration_array = np.zeros(90,)    
    for dk in duration_keys:
        duration_array[dk] = all_durations[dk]/3600
    values_binned = [sum(duration_array[interval[0]:interval[1]+1]) for interval in sum_intervals]    
    logging.info(count) ## nb jobs greater than 1
    startdate,enddate = rf.range_months()
    logging.info(str(startdate)+" "+str(enddate))
    fig,ax = plt.subplots(2,1,sharex = False)
    ax[0].hist(all_parallelism,bins = bins,log = True,edgecolor = "black")
    ax[0].set_ylabel("Total Job Count")
    ax[0].set_xscale("log",basex = base)
    ax[0].tick_params(
    axis='x',          # changes apply to the x-axis
    which='both',      # both major and minor ticks are affected
    labelbottom=False,
    bottom = False) # labels along the bottom edge are off
    #ax[1].bar(duration_keys,duration_values)
    #ax[1].bar([i for i in range(len(values_binned))],values_binned)
    ax[1].bar(bins[:-1],values_binned,width = np.diff(bins),log = True,ec = "k",align = "edge")
    ax[1].set_yscale('log')
    ax[1].set_xscale('log',basex = base)
    ax[1].set_xlabel("Number of datasets per job")
    ax[1].set_ylabel("Total Compute Hours")
    ax[0].set_title("Job size statistics for NeuroCAAS web service, {} to {}".format(startdate,enddate))

    plt.tight_layout()
    now = str(datetime.datetime.now())

    plt.savefig(os.path.join(path,f"parallelism_figure_{now}.png"))



