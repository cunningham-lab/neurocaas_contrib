## Script to handle dlc predict given appropriate input data. 
import os
import deeplabcut 
import click
import yaml

@click.command(help = "predict on new videos with network")
@click.option("--config-file","-c",type = click.Path(file_okay = True,exists=True))
@click.option("--test","-t",type=click.BOOL,is_flag = True)
def predict(config_file,test):
    """Runs prediction given a configuration file and labeled data- steps F,G,H,I of DLC guide. (https://github.com/DeepLabCut/DeepLabCut/blob/master/docs/standardDeepLabCut_UserGuide.md) 

    :param config_file: Configuration file path
    """
    
    # Parse the configuration file:
    try:
        with open(config_file,"r") as f:
            configdict = yaml.safe_load(f)
    except yaml.YAMLError as e:  
        print("DLC config.yaml file not found in model folder. Exiting.")
        raise

    # I 
    try:
        videos = configdict["video_sets"]
        for videopath,videovals in videos.items():
            if videovals.get("crop",False):
                try:
                    deeplabcut.analyze_videos(config_file,os.path.join(os.path.dirname(config_file),videopath),cropping = True)
                except TypeError:    
                    print("Cropping not formatted correctly for DLC 2.1. Proceeding without cropping.")
                    deeplabcut.analyze_videos(config_file,os.path.join(os.path.dirname(config_file),videopath))
            else:    
                deeplabcut.analyze_videos(config_file,os.path.join(os.path.dirname(config_file),videopath))

    except KeyError:    
        print("No field 'video_sets: will not analyze videos after training.")
    

if __name__ == "__main__":
    predict()
