from __future__ import generators
import os
import requests
import logging
import json
import jsonschema

from cfn_resource_provider import default_injecting_validator

log = logging.getLogger()


def is_int(s):
    """
    returns true, if the string is a proper decimal integer value
    """
    if s[0] in ('-', '+'):
        return s[1:].isdigit()
    return s.isdigit()


class ResourceProvider(object):
    """
    Custom CloudFormation Resource Provider. Just
    """

    def __init__(self):
        """
        constructor
        """
        self.request = None
        self.response = None
        self.context = None
        """
        default json schema for request['ResourceProperties']. Override in your subclass.
        """
        self.request_schema = {'type': 'object'}

    @property
    def custom_cfn_resource_name(self):
        return 'Custom::%s' % self.__class__.__name__.replace('Provider', '')

    def set_request(self, request, context):
        """
        sets the lambda request to process.
        """
        self.request = request
        self.context = context
        self.response = {
            'Status': 'SUCCESS',
            'Reason': '',
            'StackId': request['StackId'],
            'RequestId': request['RequestId'],
            'LogicalResourceId': request['LogicalResourceId'],
            'PhysicalResourceId': request['PhysicalResourceId'] if 'PhysicalResourceId' in request else None,
            'Data': {}
        }

    def get(self, name, default=None):
        """
        returns the custom resource property `name` if it exists, otherwise `default`
        """
        return self.properties[name] if name in self.properties else default

    @property
    def properties(self):
        """
        returns the custom resource properties from the request.
        """
        return self.request['ResourceProperties']

    @property
    def logical_resource_id(self):
        """
        returns the LogicaLResourceId from the request.
        """
        return self.request['LogicalResourceId']

    @property
    def stack_id(self):
        """
        returns the StackId from the request.
        """
        return self.request['StackId']

    @property
    def request_id(self):
        """
        returns the RequestId from the request.
        """
        return self.request['RequestId']

    @property
    def response_url(self):
        """
        returns the ResponseURL from the request.
        """
        return self.request['ResponseURL']

    @property
    def physical_resource_id(self):
        """
        returns the PhysicalResourceId from the response. Initialized from request.
        """
        return self.response['PhysicalResourceId']

    @physical_resource_id.setter
    def physical_resource_id(self, new_resource_id):
        self.response['PhysicalResourceId'] = new_resource_id

    @property
    def request_type(self):
        """
        returns the CloudFormation request type.
        """
        return self.request['RequestType']

    @property
    def reason(self):
        """
        returns the CloudFormation reason for the status.
        """
        return self.response['Reason']

    @property
    def status(self):
        """
        returns the response status, 'FAILED' or 'SUCCESS'
        """
        return self.response['Status']

    @property
    def resource_type(self):
        """
        returns the CloudFormation resource type on which to perform the request.
        """
        return self.request['ResourceType']

    def is_valid_cfn_request(self):
        """
        returns true when self.request is a valid CloudFormation custom resource request, otherwise false.
        if false, sets self.status and self.reason.
        """
        try:
            jsonschema.validate(self.request, self.cfn_request_schema)
            return True
        except jsonschema.ValidationError as e:
            self.fail('invalid CloudFormation Request received: %s' % str(e))
            return False

    def is_valid_cfn_response(self):
        """
        returns true when self.response is a valid CloudFormation custom resource response, otherwise false.
        if false, it logs the reason.
        """
        try:
            jsonschema.validate(
                self.response, ResourceProvider.cfn_response_schema)
            return True
        except jsonschema.ValidationError as e:
            log.warn('invalid CloudFormation response created: %s', str(e))
            return False

    def convert_property_types(self):
        """
        allows you to coerce the values in properties to be the type expected. Stupid CFN sends all values as Strings..
        it is called before the json schema validation takes place.

        one day we will make it a generic method, not now...
        """
        pass

    def heuristic_convert_property_types(self, properties):
        """
        heuristic type conversion of string values in `properties`.
        """
        for name in properties:
            if isinstance(properties[name], dict):
                self.heuristic_convert_property_types(properties[name])
            elif isinstance(properties[name], (str, unicode)):
                v = str(properties[name])
                if v == 'true':
                    properties[name] = True
                elif v == 'false':
                    properties[name] = False
                elif is_int(v):
                    properties[name] = int(v)
                else:
                    pass  # leave it a string.

    def is_valid_request(self):
        """
        returns true if `self.properties` is a valid request as specified by the JSON schema self.request_schema, otherwise False.
        Optional properties with a default value in the schema will be added to self.porperties.
        If false, self.reason and self.status are set.
        """
        try:
            self.convert_property_types()
            default_injecting_validator.validate(self.properties, self.request_schema)
            return True
        except jsonschema.ValidationError as e:
            log.error('invalid resource properties: %s' % str(e))
            return False

    def set_attribute(self, name, value):
        """
        sets the attribute `name` to `value`. This value can be retrieved using "Fn::GetAtt".
        """
        self.response['Data'][name] = value

    def get_attribute(self, name):
        """
        returns the value of the attribute `name`.
        """
        return self.response['Data'][name] if name in self.response['Data'] else None

    def success(self, reason=None):
        """
        sets response status to SUCCESS, with an optional reason.
        """
        self.response['Status'] = 'SUCCESS'
        if reason is not None:
            self.response['Reason'] = reason

    def fail(self, reason):
        """
        sets response status to FAILED
        """
        self.response['Status'] = 'FAILED'
        self.response['Reason'] = reason

    def create(self):
        """
        create the custom resource
        """
        self.fail('create not implemented by %s' % self)

    def update(self):
        """
        update the custom resource
        """
        self.fail('update not implemented by %s' % self)

    def delete(self):
        """
        delete the custom resource
        """
        self.success('delete not implemented by %s' % self)

    def execute(self):
        """
        execute the request.
        """
        if not self.is_valid_cfn_request():
            if 'RequestType' in self.request and self.request_type == 'Delete':
                self.success()
            return

        if self.resource_type != self.custom_cfn_resource_name:
            self.fail('ResourceType %s not supported by provider %s' %
                      (self.resource_type, self.custom_cfn_resource_name))
            if self.request_type == 'Delete':
                # failure to delete an invalid request hangs your cfn...
                self.success()
            return

        if self.is_valid_request():
            if self.request_type == 'Create':
                self.create()
            elif self.request_type == 'Update':
                self.update()
            else:
                assert self.request_type == 'Delete'
                self.delete()
        elif self.request_type == 'Delete':
            # failure to delete an invalid request hangs your cfn...
            self.success()

    def handle(self, request, context):
        """
        handles the CloudFormation request.
        """
        log.debug('received request %s', json.dumps(request))
        self.set_request(request, context)
        self.execute()
        self.send_response()
        return self.response

    def send_response(self):
        """
        sends the response to `ResponseURL`
        """
        self.is_valid_cfn_response()
        url = self.request['ResponseURL']
        log.debug('sending response to %s request %s',
                  url, json.dumps(self.response))
        r = requests.put(url, json=self.response)
        if r.status_code != 200:
            raise Exception('failed to put the response to %s status code %d, %s' %
                            (url, r.status_code, r.text))

    """
    A JSON Schema which defines a proper CloudFormation response message
    """
    cfn_response_schema = {
        "required": ["Status", "Reason", "RequestId", "StackId",
                     "LogicalResourceId", "PhysicalResourceId", "Data"],
        "properties": {
            "Status": {"type": "string", "enum": ["SUCCESS", "FAILED"]},
            "StackId": {"type": "string"},
            "RequestId": {"type": "string"},
            "LogicalResourceId": {"type": "string"},
            "PhysicalResourceId": {"type": "string"},
            "Data": {"type": "object"}
        }
    }

    """
    A JSON Schema which defines a proper CloudFormation request message
    """
    cfn_request_schema = {
        "type": "object",
        "required": ["RequestType", "ResponseURL", "StackId", "RequestId", "ResourceType",
                     "LogicalResourceId", "ResourceProperties"],
        "properties": {
            "RequestType": {"type": "string", "enum": ["Create", "Update", "Delete"]},
            "ResponseURL": {"type": "string", "format": "uri", "pattern": "^https?://"},
            "StackId": {"type": "string"},
            "RequestId": {"type": "string"},
            "ResourceType": {"type": "string"},
            "LogicalResourceId": {"type": "string"},
            "PhysicalResourceId": {"type": "string"},
            "ResourceProperties": {"type": "object"}
        }
    }
