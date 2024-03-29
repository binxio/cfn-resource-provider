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

        def update(self):
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


**Processing boolean and integer properties**

AWS CloudFormation passes all properties in  string format, eg 'true', 'false', '123'. This does not go down well with the json schema validator. Therefore, before the validator is called, it calls the method `convert_property_types`. Use this method to do the conversion of the non string properties::

   def convert_property_types(self):
        try:
            if 'Length' in self.properties and isinstance(self.properties['Length'], (str, unicode,)):
                self.properties['Length'] = int(self.properties['Length'])
            if 'ReturnSecret' in self.properties and isinstance(self.properties['ReturnSecret'], (str, unicode,)):
                self.properties['ReturnSecret'] = (self.properties['ReturnSecret'] == 'true')
        except ValueError as e:
            log.error('failed to convert property types %s', e)

it is ok if you cannot convert the values: the validator will report the error for you :-)

Alternatively, you may use the `heuristic_convert_property_types` method::

   def convert_property_types(self):
        self.heuristic_convert_property_types(self.properties)

it will convert all integer strings to int type, and 'true' and 'false' strings to a boolean type. Recurses through your dictionary.

**Using SNS Backed custom resource provider**

Next to AWS Lambda you can also use a SNS Topic to handle your custom resources. AWS calls these `Amazon Simple Notification Service-backed custom resources <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-custom-resources-sns.html>`_.
When you subscribe your AWS Lambda function to this topic the `event` structure is different than when you directly invoke the Lambda function using a custom resource.
The payload of a Lambda function that is invoked via a SNS Topic contains 1 or more events. For this reason we provide a `SnsEnvelope` class that will process each event in the event::

    def handler(request, context):
        provider = SnsEnvelope(SampleProvider)
        requests = provider.handle(request, context)

The `SampleProvider` is the same provider that you directly would use. But by passing it into the envelope class it will be used for each event in the payload.
