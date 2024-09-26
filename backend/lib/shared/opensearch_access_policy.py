from constructs import Construct

from aws_cdk import (
    aws_opensearchservice as aos,
    aws_iam as iam,
    aws_ec2 as ec2
)

class OpenSearchAccessPolicy(Construct):
    def __init__(self, scope: Construct, construct_id: str, 
        domain: aos.IDomain,
        grantee_principal: iam.IPrincipal,
        domain_read_access: bool=False,
        domain_write_access: bool=False,
        index_read_access: bool=True,
        index_write_access: bool=False,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # domain.add_access_policies(iam.PolicyStatement(
        #     actions=['es:*'],
        #     principals=[
        #         grantee_principal,
        #     ],
        #     resources=[
        #         f"arn:aws:es:*:*:domain/{domain.domain_name}",
        #         f"arn:aws:es:*:*:domain/{domain.domain_name}/*",
        #         f"arn:aws:es:*:*:domain/{domain.domain_name}/*/*"
        #     ]
        # ))
        if domain_write_access:
            if domain_read_access:
                domain.grant_read_write(grantee_principal)
            else:
                domain.grant_write(grantee_principal)
        elif domain_read_access:
            domain.grant_read(grantee_principal)
        
        if index_write_access:
            if index_read_access:
                domain.grant_index_read_write("*", grantee_principal)
            else:
                domain.grant_index_write("*", grantee_principal)
        elif index_read_access:
            domain.grant_index_read("*", grantee_principal)