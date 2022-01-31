import pytest 
import datetime
import pdb
import json
import neurocaas_contrib
from testpaths import get_dict_file 
from neurocaas_contrib.remote import NeuroCAASAMI
import localstack_client.session
import os
from test_cli_commands import groupname

filepath = os.path.realpath(__file__)
testpath = os.path.dirname(filepath)
test_mats = os.path.join(testpath,"test_mats")

session = localstack_client.session.Session()
ec2_resource = session.resource("ec2")
ec2_client = session.client("ec2")
s3 = session.resource("s3")
ssm_client = session.client("ssm")
sts = session.client("sts")

@pytest.fixture
def mock_boto3_for_remote(monkeypatch):
    monkeypatch.setattr(neurocaas_contrib.remote,"ec2_resource",ec2_resource)
    monkeypatch.setattr(neurocaas_contrib.remote,"ec2_client",ec2_client)
    monkeypatch.setattr(neurocaas_contrib.remote,"s3",s3)
    monkeypatch.setattr(neurocaas_contrib.remote,"ssm_client",ssm_client)
    monkeypatch.setattr(neurocaas_contrib.remote,"sts",sts)
    instance = ec2_resource.create_instances(MaxCount = 1,MinCount=1)[0]
    ami = ec2_client.create_image(InstanceId=instance.instance_id,Name = "dummy")
    ec2_resource.create_security_group(GroupName=groupname,Description = "creating security group here")
    yield ami["ImageId"]
    ec2_client.delete_security_group(GroupName=groupname)

class Test_NeuroCAASAMI():
    def test_init(self,mock_boto3_for_remote):
        ami = NeuroCAASAMI(os.path.join(test_mats))

    def test_launch_devinstance(self,mock_boto3_for_remote):
        amiid = mock_boto3_for_remote
        ami = NeuroCAASAMI(os.path.join(test_mats))
        ami.config["Lambda"]["LambdaConfig"]["AMI"] = amiid
        ami.launch_devinstance()
        ec2_client.terminate_instances(InstanceIds=[ami.instance.instance_id])
        assert ami.instance.image_id == amiid

    def test_create_devami(self,mock_boto3_for_remote):
        amiid = mock_boto3_for_remote
        ami = NeuroCAASAMI(os.path.join(test_mats))
        ami.config["Lambda"]["LambdaConfig"]["AMI"] = amiid
        ami.launch_devinstance()
        ami.create_devami("testami")
        ec2_client.terminate_instances(InstanceIds=[ami.instance.instance_id])
        assert ami.instance.image_id == amiid
        assert ami.ami_hist[0]["ResponseMetadata"]["HTTPStatusCode"] == 200

    def test_submit_job(self,mock_boto3_for_remote,tmp_path):
        submit = tmp_path / "submit.json"
        submit.write_text(json.dumps({"dataname":"zz","configname":"yy","timestamp":"uu"}))
        amiid = mock_boto3_for_remote
        ami = NeuroCAASAMI(os.path.join(test_mats))
        ami.config["Lambda"]["LambdaConfig"]["AMI"] = amiid
        ami.launch_devinstance()
        ami.create_devami("testami")
        with pytest.raises(Exception):
            ami.submit_job(submit)
        ec2_client.terminate_instances(InstanceIds=[ami.instance.instance_id])
        assert ami.instance.image_id == amiid
        assert ami.ami_hist[0]["ResponseMetadata"]["HTTPStatusCode"] == 200

    @pytest.mark.parametrize("condition",["empty","full"])
    def test_to_dict(self,mock_boto3_for_remote,tmp_path,condition):
        tempdir = tmp_path / "dir"
        tempdir.mkdir()
        config = tempdir / "dict.json"
        if condition == "full":
            submit = tmp_path / "submit.json"
            submit.write_text(json.dumps({"dataname":"zz","configname":"yy","timestamp":"uu"}))
            amiid = mock_boto3_for_remote
            ami = NeuroCAASAMI(os.path.join(test_mats))
            ami.config["Lambda"]["LambdaConfig"]["AMI"] = amiid
            ami.launch_devinstance()
            ami.create_devami("testami")
            with pytest.raises(Exception):
                ami.submit_job(submit)
            ec2_client.terminate_instances(InstanceIds=[ami.instance.instance_id])
        elif condition == "empty":    
            ami = NeuroCAASAMI(os.path.join(test_mats))
        ddict = ami.to_dict()
        print(ddict)
        config.write_text(json.dumps(ddict)) ## successful write = pass

    @pytest.mark.parametrize("condition",["empty","full","full_noinst"])
    def test_from_dict(self,mock_boto3_for_remote,tmp_path,condition):
        tempdir = tmp_path / "dir"
        tempdir.mkdir()
        config = tempdir / "dict.json"
        if condition in ["full","full_noinst"]:
            submit = tmp_path / "submit.json"
            submit.write_text(json.dumps({"dataname":"zz","configname":"yy","timestamp":"uu"}))
            amiid = mock_boto3_for_remote
            ami = NeuroCAASAMI(os.path.join(test_mats))
            ami.config["Lambda"]["LambdaConfig"]["AMI"] = amiid
            ami.launch_devinstance()
            ami.create_devami("testami")
            with pytest.raises(Exception):
                ami.submit_job(submit)
            ec2_client.terminate_instances(InstanceIds=[ami.instance.instance_id])
        elif condition == "empty":    
            ami = NeuroCAASAMI(os.path.join(test_mats))
        ddict = ami.to_dict()
        config.write_text(json.dumps(ddict)) ## successful write = pass
        ## compare: 
        with open(config) as f:
            dict_recovered = json.load(f)
        if condition in ["empty","full"]:
            ami2 = NeuroCAASAMI.from_dict(dict_recovered)
            for k,v in ami.__dict__.items():
                assert ami2.__dict__[k] == v
        else:
            dict_recovered["instance_id"] = "noexists"
            dict_recovered["instance_hist"] = ["garb","age"]
            ami2 = NeuroCAASAMI.from_dict(dict_recovered)
            for k,v in ami.__dict__.items():
                if k in ["instance","instance_hist"]:
                    pass
                else:
                    assert ami2.__dict__[k] == v
    
    @pytest.mark.skipif(get_dict_file() == "ci",reason = "Skipping test that relies on github creds")
    def test_update_blueprint(self,mock_boto3_for_remote,tmp_path):
        ami = NeuroCAASAMI(os.path.join(test_mats))
        ami.config["Addfield"] = "zz"
        # First try with failure: 
        with pytest.raises(AssertionError):
            ami.update_blueprint()
        # Now try with an ami id in place: 
        ami_id = mock_boto3_for_remote
        ami.update_blueprint(ami_id = ami_id)
        with open(os.path.join(test_mats,"stack_config_template.json")) as f:
            blueprint = json.load(f) 
        assert blueprint["Lambda"]["LambdaConfig"]["AMI"] == ami_id
        assert not blueprint.get("Addfield",False)







