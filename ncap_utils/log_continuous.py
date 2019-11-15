import sys
import os
import time

if __name__ == "__main__":
    filename = sys.argv[1]
    with open(filename,"w") as f:
        for i in range(100):
            f.write("{} seconds have passed now.\n".format(i))
            f.write("last command issued was {}".format(os.environ["$?"]))
            f.flush()
            time.sleep(1)


