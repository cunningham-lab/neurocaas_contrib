import pytest
import os
from testpaths import get_dict_file 
from neurocaas_contrib.connect import SSHConnection,FTPConnection

## This test suite depends entirely upon a particular ec2 instance. Not clear the best way to improve this beyond mocking everything :( 
loc = os.path.realpath(__file__)
testdir = os.path.dirname(loc)

connection_ip = "54.157.238.198"

if get_dict_file() == "ci":
    pytest.skip("skipping tests that rely upon an aws instance to host.", allow_module_level=True)

class Test_SSHConnection():
    def test_SSHConnection(self):
        with SSHConnection(connection_ip,"ubuntu","/Users/taigaabe/.ssh/id_rsa_remote_docker") as ssh:
            stdin,stdout,stderr = ssh.exec_command("cat /etc/os-release")
            listed = stdout.read().decode("utf-8")
        conditions = ["NAME=\"Ubuntu\"","ID=ubuntu","ID_LIKE=debian","UBUNTU_CODENAME=bionic"]
        for condition in conditions:
            assert condition in listed

    def test_SSHConnection_preinit(self):
        ssh = SSHConnection(connection_ip,"ubuntu","/Users/taigaabe/.ssh/id_rsa_remote_docker") 
        with ssh:
            stdin,stdout,stderr = ssh.exec_command("cat /etc/os-release")
            listed = stdout.read().decode("utf-8")
        conditions = ["NAME=\"Ubuntu\"","ID=ubuntu","ID_LIKE=debian","UBUNTU_CODENAME=bionic"]
        for condition in conditions:
            assert condition in listed

class Test_FTPConnection():
    def test_FTPConnection(self):
        with FTPConnection(connection_ip,"ubuntu","/Users/taigaabe/.ssh/id_rsa_remote_docker") as ftp:
            print("chilling")

    def test_FTPConnection_put(self):
        localfile = os.path.join(testdir,"test_mats","object.txt")
        remoteloc = "/home/ubuntu/ftpobj.txt"
        with FTPConnection(connection_ip,"ubuntu","/Users/taigaabe/.ssh/id_rsa_remote_docker") as ftp:
            ftp.put(localfile,remoteloc)

    def test_FTPConnection_put_deep(self):
        localfile = os.path.join(testdir,"test_mats","object.txt")
        remoteloc = "/home/ubuntu/new_put_dir/ftpobj.txt"
        with pytest.raises(FileNotFoundError):
            with FTPConnection(connection_ip,"ubuntu","/Users/taigaabe/.ssh/id_rsa_remote_docker") as ftp:
                ftp.put(localfile,remoteloc)

    def test_FTPConnection_get(self):
        remoteloc = "/home/ubuntu/ftpobj.txt"
        localfile = os.path.join(testdir,"test_mats","ftpobj.txt")
        with FTPConnection(connection_ip,"ubuntu","/Users/taigaabe/.ssh/id_rsa_remote_docker") as ftp:
            ftp.get(remoteloc,localfile)

    def test_FTPConnection_exists(self):
        localfile = os.path.join(testdir,"test_mats","object.txt")
        remoteloc = "/home/ubuntu/ftpobj.txt"
        ftp =FTPConnection(connection_ip,"ubuntu","/Users/taigaabe/.ssh/id_rsa_remote_docker")
        with ftp:
            ftp.put(localfile,remoteloc)
        with ftp:
            assert ftp.exists(remoteloc)
        with ftp:
            assert ftp.exists("/home/ubuntu/")
        with ftp:
            assert not ftp.exists("garbage.com")

    def test_FTPConnection_mkdir(self):
        ftp =FTPConnection(connection_ip,"ubuntu","/Users/taigaabe/.ssh/id_rsa_remote_docker")
        dirname = "/home/ubuntu/new_dir"
        with ftp:
            code = ftp.mkdir(dirname)
            print(code)
            ftp.ftp_client.rmdir(dirname)

    @pytest.mark.parametrize("precreate",[True,False])
    def test_FTPConnection_mkdir_notexists(self,precreate):        
        ftp =FTPConnection(connection_ip,"ubuntu","/Users/taigaabe/.ssh/id_rsa_remote_docker")
        notexistsdir = "/home/ubuntu/mkdir_notexistsdir"
        if precreate is True:
            with ftp:
                ftp.mkdir(notexistsdir)
        with ftp:
            ftp.mkdir_notexists(notexistsdir)
        with pytest.raises(OSError):
            with ftp:
                ftp.mkdir(notexistsdir)
        with ftp:
            ftp.ftp_client.rmdir(notexistsdir)

    def test_FTPConnection_mkdir_r_notexists(self):
        ftp =FTPConnection(connection_ip,"ubuntu","/Users/taigaabe/.ssh/id_rsa_remote_docker")
        deepdir = "/home/ubuntu/a/b/c/d/e"
        with ftp:
            ftp.mkdir_r_notexists(deepdir)
        with ftp:
            ftp.ftp_client.rmdir(deepdir)
        with ftp:
            ftp.ftp_client.rmdir("/home/ubuntu/a/b/c/d")
        with ftp:
            ftp.ftp_client.rmdir("/home/ubuntu/a/b/c")
        with ftp:
            ftp.ftp_client.rmdir("/home/ubuntu/a/b")
        with ftp:
            ftp.ftp_client.rmdir("/home/ubuntu/a")

    def test_FTPConnection_r_put(self):
        ftp =FTPConnection(connection_ip,"ubuntu","/Users/taigaabe/.ssh/id_rsa_remote_docker")
        remotedir = "/home/ubuntu/r_put_mats/"
        localpath = os.path.join(testdir,"test_mats","test_analysis","io-dir_min") 
        with ftp:
            ftp.r_put(localpath,remotedir)
        with ftp:
            assert ftp.isdir(remotedir)
            assert ftp.isdir(os.path.join(remotedir,"inputs")) 
            assert ftp.exists(os.path.join(remotedir,"inputs/file.txt")) 
        with ftp:
            ftp.rm(remotedir)
        
    def test_FTPConnection_r_get(self):
        ftp =FTPConnection(connection_ip,"ubuntu","/Users/taigaabe/.ssh/id_rsa_remote_docker")
        remotedir = "/home/ubuntu/r_put_mats/"
        localpath_put = os.path.join(testdir,"test_mats","test_analysis","io-dir_min") 
        localpath_get = os.path.join(testdir,"test_mats","test_analysis","io-dir_min_get") 
        with ftp:
            ftp.r_put(localpath_put,remotedir)
            ftp.put(os.path.join(localpath_put,"inputs/file.txt"),os.path.join(remotedir,"results/file.txt"))
        with ftp:
            ftp.r_get(remotedir,localpath_get)
        with ftp:
            ftp.rm(remotedir)
        assert os.path.exists(os.path.join(localpath_get,"results/file.txt"))




         





