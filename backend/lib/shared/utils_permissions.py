from constructs import Construct
from aws_cdk import (
    aws_iam as iam
)

class UtilsPermissions(Construct):
    def __init__(self, scope: Construct, construct_id: str, 
        function_role: iam.IRole,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        function_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "cognito-identity:GetId",
                "cognito-idp:GetUser"
            ],
            resources=["*"]
        ))

        