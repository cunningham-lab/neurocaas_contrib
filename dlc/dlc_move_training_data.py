## Script to move training data from one DLC directory to another to start training. Depends upon correctly reading an analysis file to initiate this.
import os 
import sys  
from shutil import copytree
sys.path.append("/home/ubuntu/DeepLabCut")
## First read in variables from the myconfig file. 
from myconfig import date, scorer, Task, Shuffles, TrainingFraction

## Define the directory names that you will be copying. 
for shuffle in Shuffles:
    for trainfrac in TrainingFraction:
        expfolder = "{t}{d}-trainset{pt}shuffle{s}".format(t = Task,d = date,pt = int(trainfrac*100),s = shuffle)
        bf = "UnaugmentedDataSet_{t}{d}".format(t = Task,d = date)
        # Copy
        copytree("/home/ubuntu/DeepLabCut/Generating_a_Training_Set/{}".format(expfolder),"/home/ubuntu/DeepLabCut/pose-tensorflow/models/{}".format(expfolder))
        copytree("/home/ubuntu/DeepLabCut/Generating_a_Training_Set/{}".format(bf),"/home/ubuntu/DeepLabCut/pose-tensorflow/models/{}".format(bf))

print(expfolder)
