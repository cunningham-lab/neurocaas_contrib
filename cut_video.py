import os
import sys
import json
from moviepy.editor import VideoFileClip



if __name__ == "__main__":
    moviefilename = sys.argv[1]
    configname = sys.argv[2]
    ## now get the clip
    movie = VideoFileClip(moviefilename)
    ## now get the config. 
    config = json.load(open(configname,"r"))
    coordinates = config["coordinates"]
    clip = movie.crop(x1=coordinates['x0'],y1=coordinates['y0'],x2=coordinates['x1'],y2=coordinates['y1']).subclip(0,10)
    ## get the moviename and mod.
    ## First add to the path:
    results_dirname = "/home/ubuntu/ncapdata/localdata/analysis_vids"
    results_basename = "".join(os.path.basename(moviefilename).split('.')[:-1])+"cropped.mp4"
    print(results_dirname,results_basename)
    clip.write_videofile(os.path.join(results_dirname,results_basename),codec = 'mpeg4',bitrate = "1500k",threads = 4,progress_bar = False)



