## script to calculate what proportion of usage is parallelized. 
import numpy as np
import matplotlib.pyplot as plt
import json 
import os
import sys

"""This script takes the output of a neurocaas_contrib calculate-parallelism run, and makes a histogram out of it. It takes a path to a directory, and will then take all of the parallel_logs json files within as its source material.  

:param path: the path to the directory.

"""

if __name__ == "__main__":
    path = sys.argv[1]
    assert path is not None, "you must provide a valid path where log info is stored."
    logfile_cands = os.listdir(path)
    logfiles = [lc for lc in logfile_cands if lc.endswith("parallel_logs.json")]
    
    all_parallelism = []
    all_durations = {} 
    for logfile in logfiles:
        print(os.path.join(path,logfile))
        try:
            with open(os.path.join(path,logfile)) as f:
                loginfo = json.load(f)
        except json.decoder.JSONDecodeError:        
            continue
        for job in loginfo.values():
            all_parallelism.append(len(job["instances"]))
            try:
                all_durations[len(job["durations"])]+=sum(job["durations"])
            except KeyError:    
                all_durations[len(job["durations"])] =sum(job["durations"])
        duration_keys = list(all_durations.keys())
        duration_values = [np.log(all_durations[v]/3600) for v in duration_keys]
    fig,ax = plt.subplots(2,1)
    print(duration_values)
    ax[0].hist(all_parallelism,bins = 25,log = True)
    ax[0].set_title("Histogram of different job sizes requested on NeuroCAAS")
    ax[0].set_xlabel("Number of instances per job")
    ax[0].set_ylabel("Count")
    ax[1].bar(duration_keys,duration_values)

    plt.tight_layout()

    plt.show()



