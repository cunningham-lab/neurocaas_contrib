## Module to manage connections with remote. 
import os
import errno
from stat import S_ISDIR
import paramiko


def splitall(path):
    """https://www.oreilly.com/library/view/python-cookbook/0596001673/ch04s16.html

    """
    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path: # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return allparts

class SSH(object):
    def __init__(self,hostname,hostuser,keypath):
        self.hostname = hostname
        self.hostuser = hostuser
        self.keypath = keypath
        self.client = paramiko.SSHClient()
        self.client.load_host_keys(keypath)
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

class SSHConnection(SSH):
    """Context Manager for paramiko managed ssh clients. From https://extsoft.pro/safely-destroying-connections-in-python/

    """

    def __enter__(self):
        """Enter the runtime context for this object.

        """
        self.client.connect(self.hostname,22,self.hostuser)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the runtime context and close connection.

        """
        if self.client:
            self.client.close()

    def exec_command(self,command):
        """Direct map to SSHClient.exec_command

        """
        return self.client.exec_command(command)

class FTPConnection(SSH):
    """Context Manager for file transfer. 

    """
    def __enter__(self):
        """Enter the runtime context and start sftp client. 

        """
        self.client.connect(self.hostname,22,self.hostuser)
        self.ftp_client = self.client.open_sftp()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the runtime context and close connection.

        """
        try:
            if self.ftp_client:
                self.ftp_client.close()
        except:
            pass
        try:
            if self.client:
                self.client.close()
        except:
            pass


    def get(self,remotepath,localpath):
        """Directly maps to paramiko.sftp_client.SFCTClient.get()

        :param remotepath: path to the remote file we want to get. 
        :param localpath: location we want to write to locally.
        """
        self.ftp_client.get(remotepath,localpath)

    def put(self,localpath,remotepath):
        """Directly maps to paramiko.sftp_client.SFCTClient.put()

        :param localpath: path to the local file we want to put. 
        :param remotepath: location we want to write to remotely. 
        """
        self.ftp_client.put(localpath,remotepath)

    def exists(self,filepath):
        """Like the os.path.exists command through paramiko's SFTP client. See https://stackoverflow.com/questions/850749/check-whether-a-path-exists-on-a-remote-host-using-paramiko

        """
        try:
            self.ftp_client.stat(filepath)
        except IOError as e:
            if e.errno == errno.ENOENT:
                return False
            raise
        else:
            return True

    def isdir(self,dirpath):
        """Checks if the given path is a directory:
        https://stackoverflow.com/questions/20507055/recursive-remove-directory-using-sftp/20507586#20507586
        :param dirpath:
        """
        try:
            return S_ISDIR(self.ftp_client.stat(dirpath).st_mode)
        except IOError:
            return False

    def rm(self,path):    
        """Recursive removal of directory. 

        :param path:
        """
        files = self.ftp_client.listdir(path = path)

        for f in files:
            filepath = os.path.join(path,f)
            if self.isdir(filepath):
                self.rm(filepath)
            else:
                self.ftp_client.remove(filepath)
        self.ftp_client.rmdir(path)
        
    def mkdir(self,dirpath):    
        """Directly maps to paramiko.sftp_client.SFPTClient.mkdir()
        :param dirpath: requested path (must be absolute)

        """
        self.ftp_client.mkdir(dirpath)
            
    def mkdir_notexists(self,dirpath):
        """Make directory only if it does not exist.
        :param dirpath: requested path (must be absolute)

        """
        if not self.exists(dirpath):
            self.mkdir(dirpath)
        else:
            pass

    def mkdir_r_notexists(self,dirpath):
        """Make a nested directory, creating new subdirectories as necessary.
        NOTE: Will not check if dirpath is a filepath. if it is, you might have overwrite issues.

        :param dirpath: requested path (must be absolute)
        """
        path_parts = splitall(dirpath)
        for i in range(len(path_parts)):
            self.mkdir_notexists(os.path.join(*path_parts[:i+2]))

    def r_put(self,localpath,remotepath):
        """When given a local directory, recursively puts contents of localpath at remotepath.     

        :param localpath: path to the local directory we want to put. 
        :param remotepath: location we want to write to remotely. 
        """
        ## First make the remote location:
        self.mkdir_r_notexists(remotepath)
        ## Now recursive put:
        gen = os.walk(localpath,topdown = True)
        for p,dirs,files in gen:
            relpath = os.path.relpath(p,localpath)
            if len(dirs) > 0: ## if there are directories, see if they exist at remote:
                for d in dirs:
                    remotedir = os.path.join(remotepath,relpath,d)
                    self.mkdir_notexists(remotedir)
            if len(files) > 0: ## if there are files, copy them:    
                for f in files:
                    localfile = os.path.join(p,f)
                    remotefile = os.path.join(remotepath,relpath,f)
                    self.put(localfile,remotefile)


    def r_get(self,remotepath,localpath):
        """When given a remote directory, recursively puts contents of remotepath at localpath. 

        :param remotepath: path to the remote directory we want to get from. 
        :param localpath: location we want to write to locally. 
        """
        ## First create local location:
        os.makedirs(localpath,exist_ok = True)
        ## Now recursive put:
        remotedir = remotepath
        localdir = localpath

        files = self.ftp_client.listdir(path = remotepath)
        for f in files:
            remoteloc = os.path.join(remotedir,f)
            localloc = os.path.join(localdir,f)
            if self.isdir(remoteloc):
                self.r_get(remoteloc,localloc)
            else:
                self.get(remoteloc,localloc)




