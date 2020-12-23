import pytest
import os
from neurocaas_contrib.connect import SSHConnection,FTPConnection

## This test suite depends entirely upon a particular ec2 instance. Not clear the best way to improve this beyond mocking everything :( 
loc = os.path.realpath(__file__)
testdir = os.path.dirname(loc)

class Test_SSHConnection():
    def test_SSHConnection(self):
        with SSHConnection("54.226.47.20","ubuntu","/Users/taigaabe/.ssh/id_rsa_remote_docker") as ssh:
            stdin,stdout,stderr = ssh.exec_command("cat /etc/os-release")
            listed = stdout.read().decode("utf-8")
        conditions = ["NAME=\"Ubuntu\"","ID=ubuntu","ID_LIKE=debian","UBUNTU_CODENAME=bionic"]
        for condition in conditions:
            assert condition in listed

    def test_SSHConnection_preinit(self):
        ssh = SSHConnection("54.226.47.20","ubuntu","/Users/taigaabe/.ssh/id_rsa_remote_docker") 
        with ssh:
            stdin,stdout,stderr = ssh.exec_command("cat /etc/os-release")
            listed = stdout.read().decode("utf-8")
        conditions = ["NAME=\"Ubuntu\"","ID=ubuntu","ID_LIKE=debian","UBUNTU_CODENAME=bionic"]
        for condition in conditions:
            assert condition in listed

class Test_FTPConnection():
    def test_FTPConnection(self):
        with FTPConnection("54.226.47.20","ubuntu","/Users/taigaabe/.ssh/id_rsa_remote_docker") as ftp:
            print("chilling")

    def test_FTPConnection_put(self):
        localfile = os.path.join(testdir,"test_mats","object.txt")
        remoteloc = "/home/ubuntu/ftpobj.txt"
        with FTPConnection("54.226.47.20","ubuntu","/Users/taigaabe/.ssh/id_rsa_remote_docker") as ftp:
            ftp.put(localfile,remoteloc)

    def test_FTPConnection_get(self):
        remoteloc = "/home/ubuntu/ftpobj.txt"
        localfile = os.path.join(testdir,"test_mats","ftpobj.txt")
        with FTPConnection("54.226.47.20","ubuntu","/Users/taigaabe/.ssh/id_rsa_remote_docker") as ftp:
            ftp.get(remoteloc,localfile)





