import json
from typing import Any, List

import jsonschema
from .resource_provider import ResourceProvider

SNS_SCHEMA = {
    "type": "object",
    "required": ["Records"],
    "additionalProperties": True,
    "properties": {
        "Records": {
            "type": "array",
            "items": { "$ref": "#/$defs/sns" }
        }
    },
    "$defs": {
        "sns": {
            "type": "object",
            "required": [ "Sns" ],
            "properties": {
                "Sns": {
                    "type": "object",
                    "required": [ "Message" ],
                    "properties": {
                        "Message": {
                            "type": "string"
                        }
                    }
                }
            }
        }
    }
}


class SnsEnvelope(object):
    """
    When custom resources are SNS backed the CloudFormation event is wrapped within the SNS structure. To make
    it easier to process these custom resources we created an Envelope that can unpack the SNS messages.
    """

    def __init__(self, resource_provider: ResourceProvider) -> None:
        self.provider = resource_provider

    def handle(self, event: dict, context: Any) -> List[dict]:
        """
        SNS payloads can hold 1 or more messages, so we need to handle each message as a custom resource.
        """
        if not self.__is_valid_sns_request(event):
            raise Exception("The provided event is not compliant with the SNS schema.")

        responses = []

        for record in event["Records"]:
            request = json.loads(record["Sns"]["Message"])

            responses.append(self.provider().handle(request, context))

        return responses


    def __is_valid_sns_request(self, event: dict) -> bool:
        try:
            jsonschema.validate(event, SNS_SCHEMA)
            return True
        except jsonschema.ValidationError as e:
            self.fail('invalid CloudFormation Request received: %s' % str(e.context))
            return False