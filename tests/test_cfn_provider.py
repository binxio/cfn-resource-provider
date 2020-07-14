from uuid import uuid4

from cfn_resource_provider import ResourceProvider


class Request(dict):
    def __init__(self, request_type, name, physical_resource_id=None):
        self.update(
            {
                "RequestType": request_type,
                "ResponseURL": "https://httpbin.org/put",
                "StackId": "arn:aws:cloudformation:us-west-2:EXAMPLE/stack-name/guid",
                "RequestId": "request-%s" % uuid4(),
                "ResourceType": "Custom::Resource",
                "LogicalResourceId": "MyCustomResource",
                "ResourceProperties": {"Name": name},
            }
        )
        if physical_resource_id:
            self["PhysicalResourceId"] = physical_resource_id


def test_is_valid_cfn_request():
    provider = ResourceProvider()
    request = Request("Create", "bla", str(uuid4()))
    provider.set_request(request, {})
    assert provider.is_valid_cfn_request(), provider.reason
    assert provider.request_id == request["RequestId"]
    assert provider.response_url == request["ResponseURL"]
    assert provider.status == "SUCCESS"
    assert provider.status == provider.response["Status"]
    assert provider.reason == provider.response["Reason"]

    provider.set_request(Request("create", "bla", str(uuid4())), {})
    assert not provider.is_valid_cfn_request()
    assert provider.status == "FAILED"
    assert provider.reason != ""
    assert provider.response["Status"] == provider.status
    assert provider.response["Reason"] == provider.reason


def test_is_valid_cfn_response():
    provider = ResourceProvider()
    provider.set_request(Request("Create", "bla", str(uuid4())), {})
    assert provider.is_valid_cfn_response(), provider.reason
    assert provider.status == "SUCCESS"
    assert provider.reason == ""
    assert provider.physical_resource_id


def test_custom_cfn_resource_name():
    provider = ResourceProvider()
    assert provider.custom_cfn_resource_name == "Custom::Resource"

    class SecretProvider(ResourceProvider):
        def __init__(self):
            pass

    provider = SecretProvider()
    assert provider.custom_cfn_resource_name == "Custom::Secret"


def test_is_supported_resource_type():
    provider = ResourceProvider()
    request = Request("Create", "bla", str(uuid4()))
    request["ResourceType"] = "Custom::Secret"
    provider.set_request(request, {})
    assert provider.is_valid_cfn_request(), provider.reason
    assert provider.is_valid_request(), provider.reason
    assert not provider.is_supported_request(), provider.reason


def test_set_request():
    provider = ResourceProvider()
    request = Request("Create", "bla", str(uuid4()))
    context = {"bla": "bla"}
    provider.set_request(request, context)
    assert provider.request == request
    assert provider.context == context
    assert provider.response is not None
    assert provider.request_type == request["RequestType"]
    assert provider.resource_type == request["ResourceType"]
    assert provider.request["StackId"] == provider.response["StackId"]
    assert provider.request["RequestId"] == provider.response["RequestId"]
    assert (
        provider.request["LogicalResourceId"] == provider.response["LogicalResourceId"]
    )
    assert (
        provider.request["PhysicalResourceId"]
        == provider.response["PhysicalResourceId"]
    )
    assert provider.logical_resource_id == provider.request["LogicalResourceId"]
    assert provider.physical_resource_id == provider.request["PhysicalResourceId"]
    assert "Data" in provider.response


def test_properties():
    request = Request("create", "bla", str(uuid4()))
    provider = ResourceProvider()
    provider.set_request(request, {})
    assert request["ResourceProperties"] == provider.properties


def test_old_properties():
    request = Request("Update", "bla", str(uuid4()))
    request["OldResourceProperties"] = {"Test": 1}
    provider = ResourceProvider()
    provider.set_request(request, {})
    assert request["OldResourceProperties"] == provider.old_properties

    del request["OldResourceProperties"]
    assert "OldResourceProperties" not in request
    assert isinstance(provider.old_properties, dict)
    assert len(provider.old_properties) == 0


def test_get():
    request = Request("create", "bla", str(uuid4()))
    request["ResourceProperties"] = {"Test": "123"}
    provider = ResourceProvider()
    provider.set_request(request, {})
    assert provider.get("Test") == "123"
    assert provider.get("Notthere") is None
    assert provider.get("Notthere", "mooi") == "mooi"


def test_get_old():
    request = Request("Update", "bla", str(uuid4()))
    request["OldResourceProperties"] = {"Test": 2}
    provider = ResourceProvider()
    provider.set_request(request, {})
    assert provider.get_old("Test") == 2
    assert provider.get_old("Notthere") is None
    assert provider.get_old("Notthere", "mooi") == "mooi"


def test_physical_resource_id():
    request = Request("Create", "bla", str(uuid4()))
    provider = ResourceProvider()
    provider.set_request(request, {})
    new_resource_id = "AAAAAAAAAAAAAAAA"
    provider.physical_resource_id = new_resource_id
    assert provider.physical_resource_id == new_resource_id
    assert provider.response["PhysicalResourceId"] == new_resource_id
    assert provider.request["PhysicalResourceId"] != provider.physical_resource_id


def test_set_attribute():
    request = Request("Create", "bla", str(uuid4()))
    provider = ResourceProvider()
    provider.set_request(request, {})
    provider.set_attribute("Secret", "123132")
    assert provider.get_attribute("Secret") == "123132"
    assert "Secret" in provider.response["Data"]
    assert provider.response["Data"]["Secret"] == "123132"


def test_success():
    request = Request("Create", "bla", str(uuid4()))
    provider = ResourceProvider()
    provider.set_request(request, {})
    provider.success("yeah!")
    assert provider.status == "SUCCESS"
    assert provider.reason == "yeah!"
    provider.fail("ohno")
    assert provider.status == "FAILED"
    assert provider.reason == "ohno"
    provider.success()
    assert provider.status == "SUCCESS"
    assert provider.reason == "ohno"


def test_invalid_type_create():
    request = Request("Create", "bla", str(uuid4()))
    request["ResourceType"] = "Custom::Secret"
    provider = ResourceProvider()
    provider.set_request(request, {})
    provider.execute()
    assert provider.physical_resource_id
    assert provider.status == "FAILED"
    assert (
        provider.reason
        == "ResourceType Custom::Secret not supported by provider Custom::Resource"
    )


def test_exception_on_create():
    class CrashProvider(ResourceProvider):
        def __init__(self):
            super(CrashProvider, self).__init__()

        def create(self):
            raise ValueError("does not work")

    provider = CrashProvider()
    request = Request("Create", "bla")
    request["ResourceType"] = "Custom::Crash"
    provider.set_request(request, {})
    provider.execute()
    assert provider.status == "FAILED"
    assert provider.physical_resource_id == "could-not-create"
    assert provider.reason == "does not work"


def test_invalid_type_delete():
    request = Request("Delete", "bla", str(uuid4()))
    request["ResourceType"] = "Custom::Secret"
    provider = ResourceProvider()
    provider.set_request(request, {})
    provider.execute()
    assert provider.status == "SUCCESS"
    assert (
        provider.reason
        == "ResourceType Custom::Secret not supported by provider Custom::Resource"
    )


def test_create():
    request = Request("Create", "bla", str(uuid4()))
    provider = ResourceProvider()
    request["ResourceType"] == provider.custom_cfn_resource_name
    provider.set_request(request, {})
    provider.execute()
    assert provider.physical_resource_id
    assert provider.status == "FAILED"
    assert provider.reason.startswith("create not implemented")


def test_update():
    request = Request("Update", "bla", str(uuid4()))
    provider = ResourceProvider()
    request["ResourceType"] == provider.custom_cfn_resource_name
    provider.set_request(request, {})
    provider.execute()
    assert provider.physical_resource_id
    assert provider.status == "FAILED"
    assert provider.reason.startswith("update not implemented")


def test_delete():
    request = Request("Delete", "bla", str(uuid4()))
    provider = ResourceProvider()
    request["ResourceType"] == provider.custom_cfn_resource_name
    provider.set_request(request, {})
    provider.execute()
    assert provider.status == "SUCCESS"
    assert provider.reason.startswith("delete not implemented")


def test_no_echo():
    request = Request("Delete", "bla", str(uuid4()))
    provider = ResourceProvider()
    provider.set_request(request, {})
    assert provider.no_echo == None
    provider.no_echo = True
    assert provider.no_echo == True
    provider.no_echo = False
    assert provider.no_echo == False

    try:
        provider.no_echo = "true"
        assert False, "no_echo set to non boolean"
    except AssertionError as e:
        pass


def test_heuristic_convert_property_types():
    provider = ResourceProvider()
    v = {
        "integer": "131",
        "negative": "-123",
        "positive": "+123",
        "true": "true",
        "false": "false",
        "badint": "1231n",
        "emptystring": u"",
    }
    provider.heuristic_convert_property_types(v)

    assert isinstance(v["emptystring"], str)

    assert isinstance(v["integer"], int)
    assert v["integer"] == 131
    assert isinstance(v["negative"], int)
    assert v["negative"] == -123
    assert isinstance(v["positive"], int)
    assert v["positive"] == 123
    assert isinstance(v["true"], bool)
    assert v["true"]
    assert isinstance(v["false"], bool)
    assert not v["false"]
    assert isinstance(v["badint"], str)
    assert v["badint"] == "1231n"

    v = {
        "ints": {"integer": "131", "negative": "-123", "positive": "+123"},
        "bools": {"true": "true", "false": "false"},
        "badint": "1231n",
    }

    provider.heuristic_convert_property_types(v)

    assert isinstance(v["ints"]["integer"], int)
    assert v["ints"]["integer"] == 131
    assert isinstance(v["ints"]["negative"], int)
    assert v["ints"]["negative"] == -123
    assert isinstance(v["ints"]["positive"], int)
    assert v["ints"]["positive"] == 123
    assert isinstance(v["bools"]["true"], bool)
    assert v["bools"]["true"]
    assert isinstance(v["bools"]["false"], bool)
    assert not v["bools"]["false"]
    assert isinstance(v["badint"], str)
    assert v["badint"] == "1231n"


def test_heuristic_convert_property_types_arrays():
    provider = ResourceProvider()

    v = {
        "ints": ["131", "-123", "+123"],
        "bools": ["true", "false"],
        "dictarray": [{"port": "80", "enabled": "true"}],
    }
    provider.heuristic_convert_property_types(v)
    e = {
        "ints": [131, -123, 123],
        "bools": [True, False],
        "dictarray": [{"port": 80, "enabled": True}],
    }
    assert v == e


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
                    "Name": {
                        "type": "string",
                        "minLength": 1,
                        "pattern": "[a-zA-Z0-9_/]+",
                    },
                    "Description": {"type": "string", "default": ""},
                    "Alphabet": {
                        "type": "string",
                        "default": "abcdfghijklmnopqrstuvwyxz",
                    },
                    "ReturnSecret": {"type": "boolean", "default": False},
                    "KeyAlias": {"type": "string", "default": "alias/aws/ssm"},
                    "Length": {"type": "integer", "default": 30},
                },
            }

        def create(self):
            pass

        def update(self):
            pass

        def delete(self):
            pass

    provider = TestSecretProvider()
    request = Request("Create", "bla", str(uuid4()))
    request["ResourceType"] = "Custom::TestSecret"
    provider.set_request(request, {})
    assert provider.is_valid_request()

    r = provider.request["ResourceProperties"]
    assert r["Length"] == 30
    assert r["Alphabet"] == provider.request_schema["properties"]["Alphabet"]["default"]
    assert not r["ReturnSecret"]
    assert r["KeyAlias"] == "alias/aws/ssm"

    del request["ResourceProperties"]["Name"]
    provider.set_request(request, {})
    assert not provider.is_valid_request()
    assert provider.status == "FAILED"
    assert (
        provider.reason == "invalid resource properties: 'Name' is a required property"
    )


def test_expose_request_value():
    class TestSecretProvider(ResourceProvider):
        """
        test provider
        """

        def __init__(self):
            super(TestSecretProvider, self).__init__()
            self.request_schema = {
                "$schema": "http://json-schema.org/draft-04/schema#",
                "type": "object",
                "oneOf": [
                    {"required": ["Database", "User", "Password"]},
                    {"required": ["Database", "User", "PasswordParameterName"]},
                    {"required": ["Database", "User", "PasswordSecretName"]},
                ],
                "properties": {
                    "Database": {"$ref": "#/definitions/connection"},
                    "User": {
                        "type": "string",
                        "pattern": "^[_$A-Za-z][A-Za-z0-9_$]*(@[.A-Za-z0-9%_$\\-]+)?$",
                        "maxLength": 32,
                        "description": "the user to create",
                    },
                    "Password": {
                        "type": "string",
                        "maxLength": 32,
                        "description": "the password for the user",
                    },
                    "PasswordParameterName": {
                        "type": "string",
                        "minLength": 1,
                        "description": "the name of the password in the Parameter Store.",
                    },
                    "PasswordSecretName": {
                        "type": "string",
                        "minLength": 1,
                        "description": "the name of the password in the Secret Manager.",
                    },
                    "WithDatabase": {
                        "type": "boolean",
                        "default": True,
                        "description": "create a database with the same name, or only a user",
                    },
                    "DeletionPolicy": {
                        "type": "string",
                        "default": "Retain",
                        "enum": ["Drop", "Retain"],
                    },
                },
                "definitions": {
                    "connection": {
                        "type": "object",
                        "oneOf": [
                            {
                                "required": [
                                    "DBName",
                                    "Host",
                                    "Port",
                                    "User",
                                    "Password",
                                ]
                            },
                            {
                                "required": [
                                    "DBName",
                                    "Host",
                                    "Port",
                                    "User",
                                    "PasswordParameterName",
                                ]
                            },
                            {
                                "required": [
                                    "DBName",
                                    "Host",
                                    "Port",
                                    "User",
                                    "PasswordSecretName",
                                ]
                            },
                        ],
                        "properties": {
                            "DBName": {
                                "type": "string",
                                "default": "mysql",
                                "description": "the name of the database",
                            },
                            "Host": {
                                "type": "string",
                                "description": "the host of the database",
                            },
                            "Port": {
                                "type": "integer",
                                "default": 3306,
                                "description": "the network port of the database",
                            },
                            "User": {
                                "type": "string",
                                "maxLength": 32,
                                "description": "the username of the database owner",
                            },
                            "Password": {
                                "type": "string",
                                "maxLength": 32,
                                "description": "the password of the database owner",
                            },
                            "PasswordParameterName": {
                                "type": "string",
                                "description": "the name of the database owner password in the Parameter Store.",
                            },
                            "PasswordSecretName": {
                                "type": "string",
                                "description": "the name of the database owner password in the Secrets Manager.",
                            },
                        },
                    }
                },
            }

        def create(self):
            pass

        def update(self):
            pass

        def delete(self):
            pass

    provider = TestSecretProvider()
    request = Request("Create", "bla", str(uuid4()))
    request["ResourceType"] = "Custom::TestSecret"
    request["ResourceProperties"] = {
        "ServiceToken": "arn:aws:lambda:eu-central-1::function:binxio-cfn-dbuser-provider-vpc",
        "User": "service112_user",
        "WithDatabase": False,
        "Password": "donotshowme",
    }
    provider.set_request(request, {})
    assert not provider.is_valid_request(), provider.reason

    assert "donotshowme" not in provider.reason

    request = Request("Create", "doesnotmatch", str(uuid4()))

def test_truncate_reason():
    provider = ResourceProvider()
    request = Request("Create", "bla", str(uuid4()))
    provider.set_request(request, {})

    reason = '--error---' * 30
    provider.reason = reason
    provider._truncate_reason()
    assert len(provider.reason) == 203, provider.reason