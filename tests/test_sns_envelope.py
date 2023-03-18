import json
from typing import List
from uuid import uuid4

import pytest

from cfn_resource_provider import SnsEnvelope
from cfn_resource_provider.resource_provider import ResourceProvider


class Request(dict):
    def __init__(self, request_type, name, physical_resource_id=None):
        self.update(
            {
                "RequestType": request_type,
                "ResponseURL": "https://httpbin.org/put",
                "StackId": "arn:aws:cloudformation:us-west-2:EXAMPLE/stack-name/guid",
                "RequestId": "request-%s" % uuid4(),
                "ResourceType": "Custom::Sample",
                "LogicalResourceId": "MyCustomResource",
                "ResourceProperties": {"Name": name},
            }
        )
        if physical_resource_id:
            self["PhysicalResourceId"] = physical_resource_id


class SampleProvider(ResourceProvider):
    def create(self) -> None:
        self.physical_resource_id = "sample-provider-create"

    def update(self) -> None:
        self.physical_resource_id = "sample-provider-update"

    def delete(self) -> None:
        self.physical_resource_id = "sample-provider-delete"


def sns_wrap(requests: List[Request]) -> dict:
    messages = map(json.dumps, requests)
    records = list(map(lambda m: {"Sns": {"Message": m}}, messages))

    return {
        "Records": records
    }


def test_sns_wrapped_single_request() -> None:
    request = Request("Create", "bla", str(uuid4()))
    provider = SnsEnvelope(SampleProvider)
    requests = provider.handle(sns_wrap([request]), {})
    assert len(requests) == 1
    assert requests[0]["PhysicalResourceId"] == "sample-provider-create"
    assert requests[0]["Status"] == "SUCCESS"
    assert requests[0]["Reason"] == ""


def test_sns_wrapped_multiple_requests() -> None:
    request1 = Request("Create", "bla", str(uuid4()))
    request2 = Request("Update", "bla", str(uuid4()))
    request3 = Request("Delete", "bla", str(uuid4()))

    provider = SnsEnvelope(SampleProvider)
    requests = provider.handle(sns_wrap([request1, request2, request3]), {})
    assert len(requests) == 3
    assert requests[0]["PhysicalResourceId"] == "sample-provider-create"
    assert requests[0]["Status"] == "SUCCESS"
    assert requests[0]["Reason"] == ""

    assert requests[1]["PhysicalResourceId"] == "sample-provider-update"
    assert requests[1]["Status"] == "SUCCESS"
    assert requests[1]["Reason"] == ""

    assert requests[2]["PhysicalResourceId"] == "sample-provider-delete"
    assert requests[2]["Status"] == "SUCCESS"
    assert requests[2]["Reason"] == ""


def test_invalid_payload() -> None:

    provider = SnsEnvelope(SampleProvider)

    with pytest.raises(Exception):
        provider.handle({}, {})

    with pytest.raises(Exception):
        provider.handle({"Records": [{"Sns": {"Foo": "Bar"}}]}, {})

