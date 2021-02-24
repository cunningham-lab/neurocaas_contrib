import pytest 
import datetime
import pdb
import neurocaas_contrib
from neurocaas_contrib.remote import NeuroCAASAMI
import localstack_client.session
import os

filepath = os.path.realpath(__file__)
testpath = os.path.dirname(filepath)
test_mats = os.path.join(testpath,"test_mats")

@pytest.fixture
def mock_boto3_for_remote(monkeypatch):
    session = localstack_client.session.Session()
    ec2_resource = session.resource("ec2")
    ec2_client = session.client("ec2")
    s3 = session.resource("s3")
    ssm_client = session.client("ssm")
    sts = session.client("sts")
    monkeypatch.setattr(neurocaas_contrib.remote,"ec2_resource",ec2_resource)
    monkeypatch.setattr(neurocaas_contrib.remote,"ec2_client",ec2_client)
    monkeypatch.setattr(neurocaas_contrib.remote,"s3",s3)
    monkeypatch.setattr(neurocaas_contrib.remote,"ssm_client",ssm_client)
    monkeypatch.setattr(neurocaas_contrib.remote,"sts",sts)

class Test_NeuroCAASAMI():
    def test_init(self,mock_boto3_for_remote):
        ami = NeuroCAASAMI(os.path.join(test_mats))



