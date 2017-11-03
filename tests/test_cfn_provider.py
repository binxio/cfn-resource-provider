import sys
import uuid
from cfn_resource_provider import ResourceProvider
from jsonschema import validate, ValidationError


class Request(dict):

    def __init__(self, request_type, name, physical_resource_id=uuid.uuid4()):
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


def test_is_valid_cfn_request():
    provider = ResourceProvider()
    request = Request('Create', 'bla', 's')
    provider.set_request(request, {})
    assert provider.is_valid_cfn_request(), provider.reason
    assert provider.stack_id == request['StackId']
    assert provider.request_id == request['RequestId']
    assert provider.response_url == request['ResponseURL']
    assert provider.status == 'SUCCESS'
    assert provider.status == provider.response['Status']
    assert provider.reason == provider.response['Reason']

    provider.set_request(Request('create', 'bla', 's'), {})
    assert not provider.is_valid_cfn_request()
    assert provider.status == 'FAILED'
    assert provider.reason != ''
    assert provider.response['Status'] == provider.status
    assert provider.response['Reason'] == provider.reason


def test_is_valid_cfn_response():
    provider = ResourceProvider()
    provider.set_request(Request('Create', 'bla', 's'), {})
    assert provider.is_valid_cfn_response(),  provider.reason
    assert provider.status == 'SUCCESS'
    assert provider.reason == ''
    assert provider.physical_resource_id


def test_custom_cfn_resource_name():
    provider = ResourceProvider()
    assert provider.custom_cfn_resource_name == 'Custom::Resource'

    class SecretProvider(ResourceProvider):

        def __init__(self):
            pass

    provider = SecretProvider()
    assert provider.custom_cfn_resource_name == 'Custom::Secret'


def test_set_request():
    provider = ResourceProvider()
    request = Request('Create', 'bla', 's')
    context = {'bla': 'bla'}
    provider.set_request(request, context)
    assert provider.request == request
    assert provider.context == context
    assert provider.response is not None
    assert provider.request_type == request['RequestType']
    assert provider.resource_type == request['ResourceType']
    assert provider.request['StackId'] == provider.response['StackId']
    assert provider.request['RequestId'] == provider.response['RequestId']
    assert provider.request[
        'LogicalResourceId'] == provider.response['LogicalResourceId']
    assert provider.request['PhysicalResourceId'] == provider.response[
        'PhysicalResourceId']
    assert provider.logical_resource_id == provider.request[
        'LogicalResourceId']
    assert provider.physical_resource_id == provider.request[
        'PhysicalResourceId']
    assert 'Data' in provider.response


def test_properties():
    request = Request('create', 'bla', 's')
    provider = ResourceProvider()
    provider.set_request(request, {})
    assert request['ResourceProperties'] == provider.properties


def test_old_properties():
    request = Request('Update', 'bla', 's')
    request['OldResourceProperties'] = {'Test': 1}
    provider = ResourceProvider()
    provider.set_request(request, {})
    assert request['OldResourceProperties'] == provider.old_properties

    del request['OldResourceProperties']
    assert 'OldResourceProperties' not in request
    assert isinstance(provider.old_properties, dict)
    assert len(provider.old_properties) == 0


def test_get():
    request = Request('create', 'bla', 's')
    request['ResourceProperties'] = {'Test': '123'}
    provider = ResourceProvider()
    provider.set_request(request, {})
    assert provider.get('Test') == '123'
    assert provider.get('Notthere') is None
    assert provider.get('Notthere', 'mooi') == 'mooi'


def test_get_old():
    request = Request('Update', 'bla', 's')
    request['OldResourceProperties'] = {'Test': 2}
    provider = ResourceProvider()
    provider.set_request(request, {})
    assert provider.get_old('Test') == 2
    assert provider.get_old('Notthere') is None
    assert provider.get_old('Notthere', 'mooi') == 'mooi'


def test_physical_resource_id():
    request = Request('Create', 'bla', 's')
    provider = ResourceProvider()
    provider.set_request(request, {})
    new_resource_id = 'AAAAAAAAAAAAAAAA'
    provider.physical_resource_id = new_resource_id
    assert provider.physical_resource_id == new_resource_id
    assert provider.response['PhysicalResourceId'] == new_resource_id
    assert provider.request[
        'PhysicalResourceId'] != provider.physical_resource_id


def test_set_attribute():
    request = Request('Create', 'bla', 's')
    provider = ResourceProvider()
    provider.set_request(request, {})
    provider.set_attribute('Secret', '123132')
    assert provider.get_attribute('Secret') == '123132'
    assert 'Secret' in provider.response['Data']
    assert provider.response['Data']['Secret'] == '123132'


def test_success():
    request = Request('Create', 'bla', 's')
    provider = ResourceProvider()
    provider.set_request(request, {})
    provider.success('yeah!')
    assert provider.status == 'SUCCESS'
    assert provider.reason == 'yeah!'
    provider.fail('ohno')
    assert provider.status == 'FAILED'
    assert provider.reason == 'ohno'
    provider.success()
    assert provider.status == 'SUCCESS'
    assert provider.reason == 'ohno'


def test_invalid_type_create():
    request = Request('Create', 'bla', 's')
    request['ResourceType'] = 'Custom::Secret'
    provider = ResourceProvider()
    provider.set_request(request, {})
    provider.execute()
    assert provider.status == 'FAILED'
    assert provider.reason == 'ResourceType Custom::Secret not supported by provider Custom::Resource'


def test_invalid_type_delete():
    request = Request('Delete', 'bla', 's')
    request['ResourceType'] = 'Custom::Secret'
    provider = ResourceProvider()
    provider.set_request(request, {})
    provider.execute()
    assert provider.status == 'SUCCESS'
    assert provider.reason == 'ResourceType Custom::Secret not supported by provider Custom::Resource'


def test_create():
    request = Request('Create', 'bla', 's')
    provider = ResourceProvider()
    request['ResourceType'] == provider.custom_cfn_resource_name
    provider.set_request(request, {})
    provider.execute()
    assert provider.status == 'FAILED'
    assert provider.reason.startswith('create not implemented')


def test_update():
    request = Request('Update', 'bla', 's')
    provider = ResourceProvider()
    request['ResourceType'] == provider.custom_cfn_resource_name
    provider.set_request(request, {})
    provider.execute()
    assert provider.status == 'FAILED'
    assert provider.reason.startswith('update not implemented')


def test_delete():
    request = Request('Delete', 'bla', 's')
    provider = ResourceProvider()
    request['ResourceType'] == provider.custom_cfn_resource_name
    provider.set_request(request, {})
    provider.execute()
    assert provider.status == 'SUCCESS'
    assert provider.reason.startswith('delete not implemented')


def test_heuristic_convert_property_types():
    provider = ResourceProvider()
    v = {'integer': '131', 'negative': '-123', 'positive': '+123',
         'true': 'true', 'false': 'false', 'badint': '1231n', 'emptystring': ''}
    provider.heuristic_convert_property_types(v)

    assert isinstance(v['emptystring'], (str, unicode))

    assert isinstance(v['integer'], int)
    assert v['integer'] == 131
    assert isinstance(v['negative'], int)
    assert v['negative'] == -123
    assert isinstance(v['positive'], int)
    assert v['positive'] == 123
    assert isinstance(v['true'], bool)
    assert v['true']
    assert isinstance(v['false'], bool)
    assert not v['false']
    assert isinstance(v['badint'], str)
    assert v['badint'] == '1231n'

    v = {'ints': {'integer': '131', 'negative': '-123', 'positive': '+123'},
         'bools': {'true': 'true', 'false': 'false'},
         'badint': '1231n'}

    provider.heuristic_convert_property_types(v)

    assert isinstance(v['ints']['integer'], int)
    assert v['ints']['integer'] == 131
    assert isinstance(v['ints']['negative'], int)
    assert v['ints']['negative'] == -123
    assert isinstance(v['ints']['positive'], int)
    assert v['ints']['positive'] == 123
    assert isinstance(v['bools']['true'], bool)
    assert v['bools']['true']
    assert isinstance(v['bools']['false'], bool)
    assert not v['bools']['false']
    assert isinstance(v['badint'], str)
    assert v['badint'] == '1231n'


def test_request_schema():
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
                    "Name": {"type": "string", "minLength": 1, "pattern": "[a-zA-Z0-9_/]+"},
                    "Description": {"type": "string", "default": ""},
                    "Alphabet": {"type": "string", "default": "abcdfghijklmnopqrstuvwyxz"},
                    "ReturnSecret": {"type": "boolean", "default": False},
                    "KeyAlias": {"type": "string", "default": "alias/aws/ssm"},
                    "Length": {"type": "integer",  "default": 30}
                }
            }

        def create(self):
            pass

        def update(self):
            pass

        def delete(self):
            pass

    provider = TestSecretProvider()
    request = Request('Create', 'bla', 's')
    request['ResourceType'] = 'Custom::TestSecret'
    provider.set_request(request, {})
    assert provider.is_valid_request()

    r = provider.request['ResourceProperties']
    assert r['Length'] == 30
    assert r['Alphabet'] == provider.request_schema[
        'properties']['Alphabet']['default']
    assert not r['ReturnSecret']
    assert r['KeyAlias'] == 'alias/aws/ssm'

    del request['ResourceProperties']['Name']
    provider.set_request(request, {})
    assert not provider.is_valid_request()
    assert provider.status == 'FAILED'
    assert provider.reason != ''
