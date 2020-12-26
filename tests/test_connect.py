import pytest
import os
from testpaths import get_dict_file 
from neurocaas_contrib.connect import SSHConnection,FTPConnection

## This test suite depends entirely upon a particular ec2 instance. Not clear the best way to improve this beyond mocking everything :( 
loc = os.path.realpath(__file__)
testdir = os.path.dirname(loc)

if get_dict_file() == "ci":
    pytest.skip("skipping tests that rely upon an aws instance to host.", allow_module_level=True)

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

    def test_FTPConnection_put_deep(self):
        localfile = os.path.join(testdir,"test_mats","object.txt")
        remoteloc = "/home/ubuntu/new_put_dir/ftpobj.txt"
        with FTPConnection("54.226.47.20","ubuntu","/Users/taigaabe/.ssh/id_rsa_remote_docker") as ftp:
            ftp.put(localfile,remoteloc)

    def test_FTPConnection_get(self):
        remoteloc = "/home/ubuntu/ftpobj.txt"
        localfile = os.path.join(testdir,"test_mats","ftpobj.txt")
        with FTPConnection("54.226.47.20","ubuntu","/Users/taigaabe/.ssh/id_rsa_remote_docker") as ftp:
            ftp.get(remoteloc,localfile)

    def test_FTPConnection_exists(self):
        localfile = os.path.join(testdir,"test_mats","object.txt")
        remoteloc = "/home/ubuntu/ftpobj.txt"
        ftp =FTPConnection("54.226.47.20","ubuntu","/Users/taigaabe/.ssh/id_rsa_remote_docker")
        with ftp:
            ftp.put(localfile,remoteloc)
        with ftp:
            assert ftp.exists(remoteloc)
        with ftp:
            assert ftp.exists("/home/ubuntu/")
        with ftp:
            assert not ftp.exists("garbage.com")

    def test_FTPConnection_mkdir(self):
        ftp =FTPConnection("54.226.47.20","ubuntu","/Users/taigaabe/.ssh/id_rsa_remote_docker")
        dirname = "/home/ubuntu/new_dir"
        with ftp:
            code = ftp.mkdir(dirname)
            print(code)
            ftp.ftp_client.rmdir(dirname)

         





