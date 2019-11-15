## Script to replace just to location in the config folder. 
import fileinput

if __name__ == "__main__":
    configname = "/home/ubuntu/DeepLabCut/myconfig_analysis.py"
    with fileinput.FileInput(configname, inplace=True, backup='.bak') as f:
        for line in f:
            if "videofolder" in line:
                #print(line)
                print("videofolder = \"/home/ubuntu/ncapdata/localdata/\"")
            elif "videotype" in line:
                print("videotype = \" mpg\"")
            else:
                print(line)

