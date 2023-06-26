import pytest 
import datetime
import pdb
from botocore.exceptions import ClientError
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
def create_instance_profile():
    profilename = "SSMRole"
    iam_resource = localstack_client.session.resource('iam')
    iam_client = localstack_client.session.client('iam')
    instance_profile = iam_resource.create_instance_profile(
    InstanceProfileName=profilename,
    Path='string'
    )
    yield instance_profile
    iam_client.delete_instance_profile(
    InstanceProfileName=profilename,
    )

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

    @pytest.mark.parametrize("test_folder",[test_mats,os.path.join(test_mats,"no_sg")])
    def test_launch_devinstance(self,mock_boto3_for_remote,create_instance_profile,test_folder):
        amiid = mock_boto3_for_remote
        ami = NeuroCAASAMI(os.path.join(test_folder))
        if test_folder.endswith("no_sg"):
            ec2_resource.create_security_group(GroupName = "testsgstack-SecurityGroupDev-1NQJIDBJG16KK",Description = "add sg for devinstance") 
        ami.config["Lambda"]["LambdaConfig"]["AMI"] = amiid
        ami.launch_devinstance("test_launch","test_launch_devinstance")
        ec2_client.terminate_instances(InstanceIds=[ami.instance.instance_id])
        if test_folder.endswith("no_sg"):
            ec2_client.delete_security_group(GroupName = "testsgstack-SecurityGroupDev-1NQJIDBJG16KK") 
        assert ami.instance.image_id == amiid
        ## tests for instance_pool
        assert ami.instance.instance_id in ami.instance_pool.keys()
        assert ami.instance_pool[ami.instance.instance_id]["name"]== "test_launch"
        assert ami.instance_pool[ami.instance.instance_id]["description"]== "test_launch_devinstance"

    def test_assign_instance(self,mock_boto3_for_remote,create_instance_profile):
        amiid = mock_boto3_for_remote
        ami = NeuroCAASAMI(os.path.join(test_mats))
        ami.config["Lambda"]["LambdaConfig"]["AMI"] = amiid
        instance = ec2_resource.create_instances(ImageId=amiid,MinCount=1,MaxCount=1)[0]
        ami.assign_instance(instance.instance_id,"assigned_inst","created assigned instance")
        with pytest.raises(ClientError):
            ami.assign_instance("bs_instance_id","bs","bs")

    @pytest.mark.parametrize("test_folder",[test_mats,os.path.join(test_mats,"no_sg")])
    def test_check_pool(self,mock_boto3_for_remote,create_instance_profile,test_folder):    
        amiid = mock_boto3_for_remote
        ami = NeuroCAASAMI(os.path.join(test_folder))
        if test_folder.endswith("no_sg"):
            ec2_resource.create_security_group(GroupName = "testsgstack-SecurityGroupDev-1NQJIDBJG16KK",Description = "add sg for devinstance") 
        ami.config["Lambda"]["LambdaConfig"]["AMI"] = amiid
        ami.launch_devinstance("test_launch1","test_launch_devinstance number 1")
        ami.launch_devinstance("test_launch2","test_launch_devinstance number 2")
        pool,active = ami.check_pool()    
        assert pool is True
        assert active is True
        ami.launch_devinstance("test_launch3","test_launch_devinstance number 3")
        ami.launch_devinstance("test_launch4","test_launch_devinstance number 4")
        if test_folder.endswith("no_sg"):
            ec2_client.delete_security_group(GroupName = "testsgstack-SecurityGroupDev-1NQJIDBJG16KK") 
        pool,active = ami.check_pool()    
        for instance_id in ami.instance_pool.keys():
            ec2_client.terminate_instances(InstanceIds=[instance_id])

        assert pool is False
        assert active is False

    def test_select_instance(self,mock_boto3_for_remote,create_instance_profile):    
        amiid = mock_boto3_for_remote
        ami = NeuroCAASAMI(os.path.join(test_mats))
        ami.config["Lambda"]["LambdaConfig"]["AMI"] = amiid
        ami.launch_devinstance("test_select_instance_1","test_select_instance number 1")
        instance1_id = ami.instance.instance_id
        ami.launch_devinstance("test_select_instance_2","test_select_instance number 2")
        instance2_id = ami.instance.instance_id
        ami.launch_devinstance("test_select_instance_3","test_select_instance number 3")
        ami.select_instance(instance_id=instance1_id)
        assert ami.instance.instance_id == instance1_id
        ami.select_instance(instance_name = "test_select_instance_2")
        assert ami.instance.instance_id == instance2_id
        
        with pytest.raises(Exception):
            ami.select_instance(instance_id="nonexistent")
        with pytest.raises(Exception):
            ami.select_instance(instance_name="nonexistent")
        with pytest.raises(Exception):
            ami.select_instance()
        for instance_id in ami.instance_pool.keys():
            ec2_client.terminate_instances(InstanceIds=[instance_id])

    def test_list_instance(self,mock_boto3_for_remote,create_instance_profile):
        amiid = mock_boto3_for_remote
        ami = NeuroCAASAMI(os.path.join(test_mats))
        ami.config["Lambda"]["LambdaConfig"]["AMI"] = amiid
        ami.launch_devinstance("test_list_instance_1","test_list_instance number 1")
        instance1_id = ami.instance.instance_id
        ami.launch_devinstance("test_list_instance_2","test_list_instance number 2")
        instance2_id = ami.instance.instance_id
        ami.launch_devinstance("test_list_instance_3","test_list_instance number 3")
        ami.launch_devinstance("test_list_instance_4","test_list_instance number 4")
        instance_info = ami.list_instances()
        assert instance_info[0].startswith("\n\nID: {} | Name: test_list_instance_1 | Status: running | Lifetime: 59m".format(instance1_id))
        assert instance_info[0].endswith("s | Description: test_list_instance number 1\n\n")
        for instance_id in ami.instance_pool.keys():
            ec2_client.terminate_instances(InstanceIds=[instance_id])

    def test_create_devami(self,create_instance_profile,mock_boto3_for_remote):
        amiid = mock_boto3_for_remote
        print(amiid)
        ami = NeuroCAASAMI(os.path.join(test_mats))
        ami.config["Lambda"]["LambdaConfig"]["AMI"] = amiid
        ami.launch_devinstance("create","test_create")
        ami.create_devami("testami")
        ec2_client.terminate_instances(InstanceIds=[ami.instance.instance_id])
        assert ami.instance.image_id == amiid
        assert ami.ami_hist[0]["ResponseMetadata"]["HTTPStatusCode"] == 200

    def test_submit_job(self,create_instance_profile,mock_boto3_for_remote,tmp_path):
        submit = tmp_path / "submit.json"
        submit.write_text(json.dumps({"dataname":"zz","configname":"yy","timestamp":"uu"}))
        amiid = mock_boto3_for_remote
        ami = NeuroCAASAMI(os.path.join(test_mats))
        ami.config["Lambda"]["LambdaConfig"]["AMI"] = amiid
        ami.launch_devinstance("test_submit_job","test_submit")
        ami.create_devami("testami")
        with pytest.raises(Exception):
            ami.submit_job(submit)
        ec2_client.terminate_instances(InstanceIds=[ami.instance.instance_id])
        assert ami.instance.image_id == amiid
        assert ami.ami_hist[0]["ResponseMetadata"]["HTTPStatusCode"] == 200

    @pytest.mark.parametrize("condition",["empty","full"])
    def test_to_dict(self,create_instance_profile,mock_boto3_for_remote,tmp_path,condition):
        tempdir = tmp_path / "dir"
        tempdir.mkdir()
        config = tempdir / "dict.json"
        if condition == "full":
            submit = tmp_path / "submit.json"
            submit.write_text(json.dumps({"dataname":"zz","configname":"yy","timestamp":"uu"}))
            amiid = mock_boto3_for_remote
            ami = NeuroCAASAMI(os.path.join(test_mats))
            ami.config["Lambda"]["LambdaConfig"]["AMI"] = amiid
            ami.launch_devinstance("test_to_dict","test writing to dict")
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
    def test_from_dict(self,create_instance_profile,mock_boto3_for_remote,tmp_path,condition):
        tempdir = tmp_path / "dir"
        tempdir.mkdir()
        config = tempdir / "dict.json"
        if condition in ["full","full_noinst"]:
            submit = tmp_path / "submit.json"
            submit.write_text(json.dumps({"dataname":"zz","configname":"yy","timestamp":"uu"}))
            amiid = mock_boto3_for_remote
            ami = NeuroCAASAMI(os.path.join(test_mats))
            ami.config["Lambda"]["LambdaConfig"]["AMI"] = amiid
            ami.launch_devinstance("test_from_dict","test from dictionary")
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
            with pytest.raises(KeyError):
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







