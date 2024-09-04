from aws_cdk import (
    NestedStack,
    aws_iam as iam,
    aws_opensearchservice as aos,
)

from constructs import Construct

from lib._final_scripts_hook.opensearch_access_policy import OpenSearchAccessPolicy

class FinalScriptsStack(NestedStack):
    def __init__(self, scope: Construct, construct_id: str, 
        domain: aos.IDomain,
        # inference_role: iam.IRole,
        ingestion_role: iam.IRole,        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        OpenSearchAccessPolicy(self, "OpenSearchAccessPolicy",
            domain=domain,
            # inference_role=inference_role,
            ingestion_role=ingestion_role
        )