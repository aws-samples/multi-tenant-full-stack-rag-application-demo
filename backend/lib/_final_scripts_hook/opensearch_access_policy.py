from constructs import Construct

from aws_cdk import (
    aws_opensearchservice as aos,
    aws_iam as iam,
    aws_ec2 as ec2
)

class OpenSearchAccessPolicy(Construct):
    def __init__(self, scope: Construct, construct_id: str, 
        domain: aos.IDomain,
        inference_role: iam.IRole,
        ingestion_role: iam.IRole,        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        domain.add_access_policies(iam.PolicyStatement(
            actions=['es:*'],
            principals=[
                ingestion_role.grant_principal,
                inference_role.grant_principal,
            ],
            resources=[
                f"arn:aws:es:{self.region}:{self.account}:domain/{self.domain.domain_name}",
                f"arn:aws:es:{self.region}:{self.account}:domain/{self.domain.domain_name}/*",
                f"arn:aws:es:{self.region}:{self.account}:domain/{self.domain.domain_name}/*/*"
            ]
        ))
        domain.grant_index_read_write("*", ingestion_role)
        domain.grant_read_write(ingestion_role)
        domain.grant_index_read("*", inference_role)