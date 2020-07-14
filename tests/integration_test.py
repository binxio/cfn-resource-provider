import sys
import uuid
from cfn_resource_provider import ResourceProvider
from jsonschema import validate, ValidationError


class Request(dict):

    def __init__(self, request_type, name, physical_resource_id=None):
        self.update({
            'RequestType': request_type,
            'ResponseURL': 'https://httpbin.org/put',
            'StackId': 'arn:aws:cloudformation:us-west-2:EXAMPLE/stack-name/guid',
            'RequestId': 'request-%s' % uuid.uuid4(),
            'ResourceType': 'Custom::Resource',
            'LogicalResourceId': 'MySecret',
            'ResourceProperties': {
                'Name': name
            }})
        if physical_resource_id is not None:
            self['PhysicalResourceId'] = physical_resource_id


def test_invoke():
    provider = ResourceProvider()
    request = Request('Create', 'bla')
    provider.handle(request, {})


def test_request_exception():
    class TestSecretProvider(ResourceProvider):
        """
        test provider
        """

        def __init__(self):
            super(TestSecretProvider, self).__init__()
            self.request_schema = {
                "type": "object",
                "required": ["Name"],
                "properties": {
                    "Name": {"type": "string", "minLength": 1}
                }
            }

        def create(self):
            raise ValueError('value error during create')

        def update(self):
            self.fail('could not update')
            raise ValueError('value exception during update')

        def delete(self):
            pass

    provider = TestSecretProvider()
    request = Request('Create', 'bla')
    request['ResourceType'] = 'Custom::TestSecret'
    provider.set_request(request, {})
    assert provider.is_valid_request()
    response = provider.handle(request, {})
    assert response['Status'] == 'FAILED', response['Reason']
    assert response['Reason'] == 'ValueError: value error during create', response['Reason']
    assert response['PhysicalResourceId'] == 'could-not-create', 'a physical resource id must be present'

    request = Request('Update', 'bla', 'resource-id')
    request['ResourceType'] = 'Custom::TestSecret'

    provider.set_request(request, {})
    assert provider.is_valid_request()
    response = provider.handle(request, {})
    assert response['Status'] == 'FAILED', response['Reason']
    assert response['Reason'] == 'could not update', 'maintain the original reason when an exception occurs'

    request = Request('Delete', 'bla', 'resource-id')
    request['ResourceType'] = 'Custom::TestSecret'
    provider.set_request(request, {})
    assert provider.is_valid_request()
    response = provider.handle(request, {})
    assert response['Status'] == 'SUCCESS', response['Reason']
