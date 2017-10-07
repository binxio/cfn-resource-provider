import sys
import uuid
from cfn_resource_provider import ResourceProvider
from jsonschema import validate, ValidationError


class Request(dict):

    def __init__(self, request_type, name, physical_resource_id=str(uuid.uuid4())):
        self.update({
            'RequestType': request_type,
            'ResponseURL': 'https://httpbin.org/put',
            'StackId': 'arn:aws:cloudformation:us-west-2:EXAMPLE/stack-name/guid',
            'RequestId': 'request-%s' % uuid.uuid4(),
            'ResourceType': 'Custom::Resource',
            'LogicalResourceId': 'MySecret',
            'PhysicalResourceId': physical_resource_id,
            'ResourceProperties': {
                'Name': name
            }})


def test_invoke():
    provider = ResourceProvider()
    request = Request('Create', 'bla')
    provider.handle(request, {})
