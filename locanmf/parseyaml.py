import sys
import yaml

if __name__ == "__main__":
    dictionary = yaml.safe_load(open(sys.argv[1],"r"))
    print(dictionary["atlas_path"])
