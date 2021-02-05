## script to calculate what proportion of usage is parallelized. 
import logging
import numpy as np
import datetime
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

:param path: the path to the directory.

"""

class RangeFinder():
    """object class to keep track of the range of dates we are considering. 

    """
    def __init__(self):
        self.form = "%Y-%m-%dT%H:%M:%SZ"
        self.baseline = datetime.datetime.now()
        ## Keep track of interval by calculating biggest and smallest differences to right now.  
        self.diff_min = np.inf
        self.diff_max = -np.inf
        self.starttime = None
        self.endtime = None
    def diff(self,datetime_str):   
        """Takes in a string formatted datetime (formatted as self.form), and compares it with now. 

        """
        timeform = datetime.datetime.strptime(datetime_str,self.form)
        diff = self.baseline-timeform
        diff_secs = diff.total_seconds()
        logging.info(diff_secs)
        return diff_secs

    def update(self,datetime_str):
        """Takes in a string formatted datetime, and updates the start and end dates if necessary.

        """
        diff = self.diff(datetime_str)
        logging.info("{}, {}, {}".format(diff,self.diff_max,self.diff_min))
        if diff > self.diff_max: 
            self.starttime = datetime_str
            self.diff_max = diff
        elif diff < self.diff_min:   
            self.endtime = datetime_str
            self.diff_min = diff
        else:    
            pass
    def return_range(self):    
        print("Started at {}, ended at {}".format(self.starttime,self.endtime))
    
    def range_months(self):
        startdate = datetime.datetime.strptime(self.starttime,self.form)
        enddate = datetime.datetime.strptime(self.endtime,self.form)
        startmonth = "{}/{}".format(startdate.month,startdate.year)
        endmonth = "{}/{}".format(enddate.month,enddate.year)
        return startmonth,endmonth

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
            if job["instances"][0]["jobpath"] in ["sawtelllab/results/job__dlc-ncap-web_1595302867","sawtelllabdlcdevelop/results/job__dlc-ncap-stable_20200720_16_47"]: 
                continue ## These are breaking bugs that also influence graph interpretation, exclude.
            all_parallelism.append(len(job["instances"]))
            ## Per job we only need one startdate.
            rf.update(job["instances"][0]["start"])
            try:
                all_durations[len(job["durations"])]+=sum(job["durations"])
            except KeyError:    
                all_durations[len(job["durations"])] =sum(job["durations"])
            if len(job["durations"]) > 40:   
                logging.warning(json.dumps(job["instances"][0],indent = 4))
                count += 1
        duration_keys = list(all_durations.keys())
        duration_values = [all_durations[v]/3600 for v in duration_keys]
    logging.info(count) ## nb jobs greater than 1
    startdate,enddate = rf.range_months()
    logging.info(str(startdate)+" "+str(enddate))
    fig,ax = plt.subplots(2,1,sharex = True)
    ax[0].hist(all_parallelism,bins = 50,log = True)
    ax[0].set_ylabel("Total Job Count")
    ax[1].bar(duration_keys,duration_values)
    ax[1].set_yscale('log')
    ax[1].set_xlabel("Number of datasets per job")
    ax[1].set_ylabel("Total Compute Hours")
    ax[0].set_title("Job size statistics for NeuroCAAS web service, {} to {}".format(startdate,enddate))

    plt.tight_layout()
    now = str(datetime.datetime.now())

    plt.savefig(os.path.join(path,f"parallelism_figure_{now}.png"))



