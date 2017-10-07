This ResourceProvider base class makes it very simple to implement a Custom CloudFormation Resource.

First, you inherit from the base class and specify a JSON schema which defines the resource properties you require::

    from cfn_resource_provider import ResourceProvider

    class SecretProvider(ResourceProvider):
        def __init__(self):
                super(SecretProvider, self).__init__()
                self.request_schema =  {
                    "type": "object",
                    "required": ["Name"],
                    "properties": {
                        "Name": {"type": "string", 
                                 "minLength": 1,
                                 "pattern": "[a-zA-Z0-9_/]+",
                                 "description": "the name of the value in the parameters store"},
                        "Description": {"type": "string", 
                                        "default": "",
                                        "description": "the description of the value in the parameter store"},
                        "Alphabet": {"type": "string",
                                     "default": "abcdfghijklmnopqrstuvwyxzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_",
                                     "description": "the characters from which to generate the secret"},
                        "ReturnSecret": {"type": "boolean",
                                         "default": False,
                                         "description": "return secret as attribute 'Secret'"},
                        "KeyAlias": {"type": "string",
                                     "default": "alias/aws/ssm",
                                     "description": "KMS key to use to encrypt the value"},
                        "Length": {"type": "integer",  
                                   "minimum": 1, "maximum": 512,
                                   "default": 30,
                                   "description": "length of the secret"}
                    }
                }

The JSON schema allows you to specify the expected properties, constraints and default values.
After that, you only need to implement the methods `create`, `update` and `delete`::

    class SecretProvider(ResourceProvider):
        ...
        def create(self):
            try:
                value = "".join(choice(self.get('Alphabet') for x in range(0, self.get('Length')))
                self.ssm.put_parameter(Name=self.get('Name'), KeyId=self.get('KeyAlias'),
                                       Type='SecureString', Overwrite=False, Value=value)
                self.set_attribute('Arn', self.arn)
                if self.get('ReturnSecret'):
                    self.set_attribute('Secret', value)

                self.physical_resource_id = self.arn
            except ClientError as e:
                self.physical_resource_id = 'could-not-create'
                self.fail(str(e))
        
        def create(self):
            ....
        
        def delete(self):
            ....

In these methods, you can safely access all the properties defined in your JSON schema. The methods
are only called after validation of the request against your schema.

- to return values which can be accessed by `Fn::GetAtt`, you can call the method `set_attribute`.
- to return a resource id for your resource, you can set the property `physical_resource_id`.
- to indicate a failed request, you can call the method `fail`.
- to indicate a succesful request, you can call the method `success`.

Finally, at the end of your module implement the AWS Lambda handle function::

    provider = SecretProvider()
    def handle(request, context):
        provider.handle(request, context)



