# Test developer bucket monitoring functions. 
from botocore.exceptions import ClientError
import pytest
import json
import logging
import os
import localstack_client.session
import neurocaas_contrib.monitor as monitor
from testpaths import get_dict_file 

if get_dict_file() == "ci":
    pytest.skip("skipping tests that rely upon logging data", allow_module_level=True)

loc = os.path.dirname(os.path.realpath(__file__))
test_log_mats = os.path.join(loc,"test_mats","test_aws_resource","test_logfolder")
bucket_name = "test-log-analysis"

session = localstack_client.session.Session()
s3_client = session.client("s3")
s3_resource = session.resource("s3")

def get_paths(rootpath):
    """Gets paths to all files relative to a given top level path. 

    """
    walkgen = os.walk(rootpath)
    paths = []
    dirpaths = []
    for p,dirs,files in walkgen:
        relpath = os.path.relpath(p,rootpath)
        if len(files) > 0 or len(dirs) > 0:
            for f in files:
                localfile = os.path.join(relpath,f)
                paths.append(localfile)
            ## We should upload the directories explicitly, as they will be treated in s3 like their own objects and we perform checks on them.    
            for d in dirs:
                localdir = os.path.join(relpath,d,"")
                if localdir == "./logs/":
                    dirpaths.append("logs/")
                else:
                    dirpaths.append(localdir)
    return paths,dirpaths            

@pytest.fixture
def setup_log_bucket(monkeypatch):
    """Sets up the module to use localstack, and creates a bucket in localstack called test-log-analysis with the following directory structure:
    /
    |-logs
      |-bendeskylab
        |-joblog1
        |-joblog2
        ...
      |-sawtelllab
        |-joblog1
        |-joblog2
        ...
    This is the minimal working example for testing a monitoring function. This assumes that we will not be mutating the state of bucket logs. 
    """
    ## Start localstack and patch AWS clients:
    session = localstack_client.session.Session()
    s3_client = session.client("s3")
    monkeypatch.setattr(monitor, "s3_client", session.client("s3")) ## TODO I don't think these are scoped correctly w/o a context manager.
    monkeypatch.setattr(monitor, "s3_resource", session.resource("s3"))

    ## Create bucket if not created:
    try:
        buckets = s3_client.list_buckets()["Buckets"]
        bucketnames = [b["Name"] for b in buckets]
        assert bucket_name in bucketnames
        yield bucket_name
    except AssertionError:    
        s3_client.create_bucket(Bucket =bucket_name)

        ## Get paths:
        log_paths,dirpaths = get_paths(test_log_mats) 
        try:
            for f in log_paths:
                s3_client.upload_file(os.path.join(test_log_mats,f),bucket_name,Key = f)
            for dirpath in dirpaths:
                s3dir = s3_resource.Object(bucket_name,dirpath)   
                s3dir.put()
        except ClientError as e:        
            logging.error(e)
            raise
        yield bucket_name    
        ## Now delete 

def test_get_analysis_cost(setup_log_bucket):    
    path = "bendeskylab"
    bucket_name = setup_log_bucket
    cost = monitor.get_analysis_cost(path,bucket_name)
    assert cost == 54.82423500000001 
    

def test_check_bucket_exists(setup_log_bucket):    
    path = "bendeskylab"
    bucket_name = setup_log_bucket
    monitor.check_bucket_exists(bucket_name) ## will assert 0 if does not exist.

def test_get_user_logs(setup_log_bucket):
    path = "bendeskylab"
    bucket_name = setup_log_bucket
    user_dict = monitor.get_user_logs(bucket_name) ## will assert 0 if does not exist.
    for key in user_dict.keys():
        assert key in ["bendeskylab","sawtelllab"]
        for log in user_dict[key]:
            log.startswith("logs/{}".format(key))        

def test_get_users(setup_log_bucket):
    bucket_name = setup_log_bucket
    l = s3_client.list_objects_v2(Bucket=bucket_name,Prefix = "logs")
    users = monitor.get_users(l)
    print(users)
    assert set(users) == set(["bendeskylab","sawtelllab"])

def test_get_jobs(setup_log_bucket):
    bucket_name = setup_log_bucket
    l = s3_client.list_objects_v2(Bucket=bucket_name,Prefix = "logs")
    jobs = monitor.get_jobs(l)
    assert len(jobs) == 290 

def test_calculate_usage(setup_log_bucket):
    path = "bendeskylab"
    bucket_name = setup_log_bucket
    user_dict = monitor.get_user_logs(bucket_name) ## will assert 0 if does not exist.
    usage_compiled = monitor.calculate_usage(bucket_name,user_dict["bendeskylab"],"bendeskylab")
    for key in usage_compiled.keys():
        assert key in ["username","cost","duration"]

@pytest.mark.parametrize("path,nb",[("sawtelllab",132),("bendeskylab",157)])
def test_calculate_parallelism(setup_log_bucket,path,nb):
    bucket_name = setup_log_bucket
    user_dict = monitor.get_user_logs(bucket_name) ## will assert 0 if does not exist.
    usage_compiled = monitor.calculate_parallelism(bucket_name,user_dict[path],path)
    logging.warning(usage_compiled.keys())
    assert sum([len(l["instances"]) for l in usage_compiled.values()]) == nb 

@pytest.mark.parametrize("path,nb",[("sawtelllab",132),("bendeskylab",157)])
def test_postprocess_jobdict(setup_log_bucket,path,nb):
    bucket_name = setup_log_bucket
    user_dict = monitor.get_user_logs(bucket_name) ## will assert 0 if does not exist.
    usage_compiled = monitor.calculate_parallelism(bucket_name,user_dict[path],path)
    usage_filtered = monitor.postprocess_jobdict(usage_compiled)
    for uf in usage_filtered.values():
        for inst in uf["instances"]:
            assert inst["start"] is not None
            assert inst["end"] is not None
        assert all([a is not None for a in uf["durations"].values()])
        

    assert sum([len(l["instances"]) for l in usage_filtered.values()]) == nb 

def test_RangeFinder():
    "WrITE ASSERTS "
    rf = monitor.RangeFinder()
    rf.update("2010-12-04T12:54:12Z")
    rf.update("2010-12-04T12:55:12Z")
    rf.return_range()
    
class Test_JobMonitor():
    def test_get_lambda_id(self,tmp_path):
        submitdict = {"dataname":"fakedata","configname":"fakeconfig","timestamp":"faketime"}
        path = str(tmp_path / "submit.json")
        with open(path, "w") as f:
            json.dump(submitdict,f)
        stackname = "cianalysispermastack"    
        jm = monitor.JobMonitor(stackname)
        pr = jm.get_lambda_id()
        assert pr.startswith("cianalysispermastack-MainLambda")

    def test_get_logs(self,tmp_path):
        """Hard to test this with fixtures. 

        """
        submitdict = {"dataname":"fakedata","configname":"fakeconfig","timestamp":"faketime"}
        path = str(tmp_path / "submit.json")
        with open(path, "w") as f:
            json.dump(submitdict,f)
        stackname = "dgp-refactor"    
        jm = monitor.JobMonitor(stackname)
        parsed = jm.get_logs(2)

    def test_print_logs(self,tmp_path):
        """Hard to test this with fixtures. 

        """
        submitdict = {"dataname":"fakedata","configname":"fakeconfig","timestamp":"faketime"}
        path = str(tmp_path / "submit.json")
        with open(path, "w") as f:
            json.dump(submitdict,f)
        stackname = "dgp-refactor"    
        jm = monitor.JobMonitor(stackname)
        jm.print_log(hours = 3)
            
    def test_get_certificate(self,tmp_path):
        submitdict = {"dataname":"reviewers/inputs/fish1_untrained.zip","configname":"reviewers/configs/fake","timestamp":"0513fish1train"}
        path = str(tmp_path / "submit.json")
        with open(path, "w") as f:
            json.dump(submitdict,f)
        stackname = "dgp-refactor"    
        jm = monitor.JobMonitor(stackname)
        cert = jm.get_certificate(path)

    def test_get_datasets(self,tmp_path):
        submitdict = {"dataname":"reviewers/inputs/fish1_untrained.zip","configname":"reviewers/configs/fake","timestamp":"0513fish1train"}
        path = str(tmp_path / "submit.json")
        with open(path, "w") as f:
            json.dump(submitdict,f)
        stackname = "dgp-refactor"    
        jm = monitor.JobMonitor(stackname)
        datasets = jm.get_datasets(path)

    def test_get_datastatus(self,tmp_path):
        submitdict = {"dataname":"reviewers/inputs/fish1_untrained.zip","configname":"reviewers/configs/fake","timestamp":"0513fish1train"}
        path = str(tmp_path / "submit.json")
        with open(path, "w") as f:
            json.dump(submitdict,f)
        stackname = "dgp-refactor"    
        jm = monitor.JobMonitor(stackname)
        status = jm.get_datastatus(path,"fish1_untrained.zip")
        print(status.rawfile)
        assert 0 
            


   

   
