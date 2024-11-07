#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import os
from aws_cdk import (
    BundlingOptions,
    CfnOutput, 
    DockerImage,
    RemovalPolicy,
    Stack, 
    aws_s3_deployment as s3_deployment,
    aws_ssm as ssm
)

from .static_site import StaticSitePublicS3, StaticSitePrivateS3


class ReactUiStack(Stack):
    def __init__(self, scope, construct_id,
        app_name: str,
        doc_collections_api_url: str,
        enabled_enrichment_pipelines: str,
        generation_api_url: str,
        identity_pool_id: str,
        ingestion_bucket_name: str,
        #initialization_api_url: str,
        prompt_templates_api_url: str,
        region: str,
        removal_policy: str,
        stack_name_backend: str,
        stack_name_frontend: str,
        user_pool_id: str,
        user_pool_client_id: str, 
        **kwargs
    ):
        super().__init__(scope, construct_id, **kwargs)
        
        self.site = StaticSitePrivateS3(
            self,
            f"UiPrivateSiteDeployment",
            # site_domain_name=domain_name,
            # hosted_zone_id=hosted_zone_id,
            # hosted_zone_name=hosted_zone_name,
        )
        
        retain_on_delete = False if removal_policy == "DESTROY" else True
        self.bucket_deployment = s3_deployment.BucketDeployment(self, 'UIBucketDeployment',
            retain_on_delete=retain_on_delete,
            destination_bucket=self.site.bucket,
            sources=[s3_deployment.Source.asset(
              'src/multi_tenant_full_stack_rag_application/ui',
              bundling=BundlingOptions(
                user="0:0",
                environment={
                    'ACCOUNT_ID': self.account,
                    'APP_NAME': app_name,
                    'DOC_COLLECTIONS_API_URL': doc_collections_api_url,
                    'ENABLED_ENRICHMENT_PIPELINES': enabled_enrichment_pipelines,
                    'GENERATION_API_URL': generation_api_url,
                    # 'INITIALIZATION_API_URL': initialization_api_url,
                    'AWS_REGION': region,
                    'INGESTION_BUCKET_NAME': ingestion_bucket_name,
                    'IDENTITY_POOL_ID': identity_pool_id,
                    'BUILD_UID': os.environ['BUILD_UID'],
                    'USER_POOL_CLIENT_ID': user_pool_client_id,
                    'USER_POOL_ID': user_pool_id,
                    'PROMPT_TEMPLATES_API_URL': prompt_templates_api_url
                },
                image=DockerImage.from_registry('alpine'),
                command=["/bin/sh", "-c", '/asset-input/build_website_deployment.sh'],
              )
            )],
            distribution_paths=['/*'], 
            distribution=self.site.distribution
        )
        # Add stack outputs
        CfnOutput(
            self,
            "SiteBucketName",
            value=self.site.bucket.bucket_name,
        )
        CfnOutput(
            self,
            "DistributionDomainName",
            value=self.site.distribution.distribution_domain_name,
        )
        
        # comment out the local dev one if you don't need it for developers
        self.ssm_param_frontend_origin_localdev =  ssm.StringParameter(self, "FrontendOriginLocalDev",
            parameter_name=f'/{stack_name_backend}/origin_frontend_localdev',
            string_value='http://localhost:5173'
        )
        
        self.ssm_param_frontend_origin =  ssm.StringParameter(self, "FrontendOrigin",
            parameter_name=f'/{stack_name_backend}/origin_frontend',
            string_value=self.site.distribution.distribution_domain_name
        )

        self.ssm_param_frontend_origin.apply_removal_policy(RemovalPolicy.DESTROY)
        # CfnOutput(
        #     self,
        #     "CertificateArn",
        #     value=self.site.certificate.certificate_arn,
        # )
