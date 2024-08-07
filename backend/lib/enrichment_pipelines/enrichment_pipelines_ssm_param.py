import json
from aws_cdk import (
    Stack,
    aws_ssm as ssm
)
from constructs import Construct

class EnrichmentPipelinesSsmParamStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, 
        param_name: str,
        param_value: [dict],
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.ssm_param = ssm.StringParameter(
            self,
            "EnrichmentPipelinesSsmParam",
            parameter_name=param_name,
            string_value=json.dumps(param_value)
        )