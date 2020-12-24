## Module to manage connections with remote. 
import errno
import paramiko

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
        
    def mkdir(self,dirpath):    
        """Directly maps to paramiko.sftp_client.SFPTClient.mkdir()
        :param path: requested path (must be absolute)

        """
        self.ftp_client.mkdir(dirpath)
            
