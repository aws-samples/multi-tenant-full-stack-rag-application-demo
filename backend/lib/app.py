#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json
import os
import yaml

from aws_cdk import (
    CfnOutput,
    CfnParameter,
    Duration,
    Stack,
    aws_dynamodb as ddb,
    aws_s3 as s3,
    aws_ssm as ssm,
)

from constructs import Construct
from pathlib import Path

from lib._final_scripts_hook.final_scripts_stack import FinalScriptsStack
from lib.auth_provider_service.auth_provider_stack import AuthProviderStack
from lib.bedrock_provider_service.bedrock_provider_stack import BedrockProviderStack
from lib.doc_collections_handler_service.doc_collections_handler_stack import DocumentCollectionsHandlerStack
from lib.embeddings_provider_service.embeddings_provider_stack import EmbeddingsProviderStack
from lib.enrichment_pipelines_handler_service.enrichment_pipelines_handler_stack import EnrichmentPipelinesHandlerStack
from lib.generation_handler_service.generation_handler_stack import GenerationHandlerStack
from lib.graph_store_provider_service.graph_store_provider_stack import GraphStoreProviderStack
from lib.ingestion_provider_service.ingestion_provider_stack import  IngestionProviderStack
from lib.prompt_template_handler_service.prompt_template_handler_stack import PromptTemplateHandlerStack
from lib.vector_store_provider_service.vector_store_provider_stack import VectorStoreProviderStack
from lib.shared.vpc import VpcStack

class MultiTenantRagStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # intialize parameters:
        param_stack_name = CfnParameter(self, 'ParamStackName',
            default=self.node.get_context('stack_name_backend')
        )
        param_removal_policy = CfnParameter(self, 'ParamRemovalPolicy',
            default=self.node.get_context('removal_policy')
        )
        param_app_name = CfnParameter(self, 'ParamAppName',
            default=self.node.get_context('app_name')
        )
        param_embeddings_model_id = CfnParameter(self, 'ParamEmbeddingsModelId',
            default=self.node.get_context('embeddings_model_id')
        )
        param_entity_extraction_model_id = CfnParameter(self, 'ParamEntityExtractionModelId',
            default=self.node.get_context('extraction_model_id')
        )
        param_ocr_model_id = CfnParameter(self, 'ParamOcrModelId',
            default=self.node.get_context('ocr_model_id')
        )
        param_allowed_email_domains = CfnParameter(self, 'ParamAllowedEmailDomains',
            default=self.node.get_context('allowed_email_domains')
        )
        param_verification_email_subject = CfnParameter(self, 'ParamVerificationEmailSubject',
            default=self.node.get_context('verification_email_subject')
        )
        param_verification_email_body = CfnParameter(self, 'ParamVerificationEmailBody',
            default=self.node.get_context('verification_email_body')
        )
        param_opensearch_data_node_ct = CfnParameter(self, 'ParamOpenSearchDataNodeCt',
            default=self.node.get_context('os_data_instance_ct')
        )
        param_opensearch_data_node_type = CfnParameter(self, 'ParamOpenSearchDataNodeType',
            default=self.node.get_context('os_data_instance_type')
        )
        param_opensearch_data_node_volume_size_gb = CfnParameter(self, 'ParamOpenSearchDataNodeVolSizeGb',
            default=self.node.get_context('os_data_instance_volume_size_gb')
        )
        param_opensearch_master_node_ct = CfnParameter(self, 'ParamOpenSearchMasterNodeCt',
            default=self.node.get_context('os_master_instance_ct')
        )
        param_opensearch_master_node_type = CfnParameter(self, 'ParamOpenSearchMasterNodeType',
            default=self.node.get_context('os_master_instance_type')
        )
        param_opensearch_multiaz_standby_enabled = CfnParameter(self, 'ParamOpenSearchMultiAzStandbyEnabled',
            default=self.node.get_context('os_multiaz_with_standby_enabled')
        )
        param_opensearch_dashboards_ec2_cert_country = CfnParameter(self, 'ParamOsDashboardsCertCountry',
            default=self.node.get_context('os_dashboards_ec2_cert_country')
        )
        param_opensearch_dashboards_ec2_cert_state = CfnParameter(self, 'ParamOsDashboardsCertState',
            default=self.node.get_context('os_dashboards_ec2_cert_state')
        )
        param_opensearch_dashboards_ec2_cert_city = CfnParameter(self, 'ParamOsDashboardsCertCity',
            default=self.node.get_context('os_dashboards_ec2_cert_city')
        )
        param_opensearch_dashboards_ec2_cert_hostname = CfnParameter(self, 'ParamOsDashboardsCertHostname',
            default=self.node.get_context('os_dashboards_ec2_cert_hostname')
        )
        param_opensearch_dashboards_ec2_cert_email_address = CfnParameter(self, 'ParamOsDashboardsCertEmailAddress',
            default=self.node.get_context('os_dashboards_ec2_cert_email_address')
        )
        param_opensearch_dashboards_ec2_enable_traffic_from_ip = CfnParameter(self, 'ParamOsDashboardsEnableTrafficFromIpCidr',
            default=self.node.get_context('os_dashboards_ec2_enable_traffic_from_ip')
        )
        param_neptune_instance_type = CfnParameter(self, 'NeptuneDbInstanceType',
            default=self.node.get_context('neptune_instance_type')
        )

        vpc_stack = VpcStack(self, 'Vpc')

        allowed_email_domains = []
        allowed_email_domains_csv = self.node.try_get_context('allowed_email_domains')
        for email_domain in allowed_email_domains_csv.split(','):
            allowed_email_domains.append(email_domain.strip())

        app_name = self.node.try_get_context('app_name')
        verification_body = self.node.try_get_context('verification_email_body').replace('{app_name}', app_name)
        auth_provider_stack = AuthProviderStack(self, 'AuthProviderStack', 
            allowed_email_domains=allowed_email_domains,
            app_security_group=vpc_stack.app_security_group,
            parent_stack_name=self.stack_name,
            verification_message_body=verification_body,
            verification_message_subject=self.node.try_get_context('verification_email_subject'),
            vpc=vpc_stack.vpc,
        )
        
        bedrock_provider_stack = BedrockProviderStack(self, 'BedrockProviderStack',
            auth_fn=auth_provider_stack.cognito_stack.cognito_auth_provider_function,
            auth_role_arn=auth_provider_stack.cognito_stack.authenticated_role_arn,
            user_pool_client_id=auth_provider_stack.cognito_stack.user_pool_client.user_pool_client_id,
            user_pool_id=auth_provider_stack.cognito_stack.user_pool.user_pool_id,
            parent_stack_name=self.stack_name,
            vpc=vpc_stack.vpc
        )

        embeddings_provider_stack = EmbeddingsProviderStack(
            self, 'EmbeddingsProviderStack',
            auth_fn=auth_provider_stack.cognito_stack.cognito_auth_provider_function,            
            auth_role_arn=auth_provider_stack.cognito_stack.authenticated_role_arn,
            embeddings_model_id=self.node.try_get_context('embeddings_model_id'),
            parent_stack_name=self.stack_name,
            user_pool_client_id=auth_provider_stack.cognito_stack.user_pool_client.user_pool_client_id,
            user_pool_id=auth_provider_stack.cognito_stack.user_pool.user_pool_id,
            vpc=vpc_stack.vpc,
        )

        ingestion_provider_stack = IngestionProviderStack(self, 'IngestionProviderStack',
            app_security_group=vpc_stack.app_security_group,
            auth_fn=auth_provider_stack.cognito_stack.cognito_auth_provider_function,
            auth_role_arn=auth_provider_stack.cognito_stack.authenticated_role_arn,
            parent_stack_name=self.stack_name,
            user_pool_client_id=auth_provider_stack.cognito_stack.user_pool_client.user_pool_client_id,
            user_pool_id=auth_provider_stack.cognito_stack.user_pool.user_pool_id,
            vpc=vpc_stack.vpc
        )

        vector_store_provider_stack = VectorStoreProviderStack(self, 'VectorStoreProviderStack',
            app_security_group=vpc_stack.app_security_group,
            auth_fn=auth_provider_stack.cognito_stack.cognito_auth_provider_function,
            auth_role_arn=auth_provider_stack.cognito_stack.authenticated_role_arn,
            cognito_identity_pool=auth_provider_stack.cognito_stack.identity_pool,
            cognito_user_pool=auth_provider_stack.cognito_stack.user_pool,
            parent_stack_name=self.stack_name,
            user_pool_client_id=auth_provider_stack.cognito_stack.user_pool_client.user_pool_client_id,
            user_pool_domain=auth_provider_stack.cognito_stack.user_pool_domain,
            user_pool_id=auth_provider_stack.cognito_stack.user_pool.user_pool_id,
            vpc=vpc_stack.vpc
        )

        doc_collections_stack = DocumentCollectionsHandlerStack(self, 'DocumentCollectionsHandlerStack',
            app_security_group=vpc_stack.app_security_group,
            auth_fn=auth_provider_stack.cognito_stack.cognito_auth_provider_function,
            auth_role_arn=auth_provider_stack.cognito_stack.authenticated_role_arn,
            cognito_identity_pool_id=auth_provider_stack.cognito_stack.identity_pool.identity_pool_id,
            cognito_user_pool_client_id=auth_provider_stack.cognito_stack.user_pool_client.user_pool_client_id,
            cognito_user_pool_id=auth_provider_stack.cognito_stack.user_pool.user_pool_id,
            parent_stack_name=self.stack_name,            
            vpc=vpc_stack.vpc
        )

        prompt_templates_handler_stack = PromptTemplateHandlerStack(self, 'PromptTemplateHandlerStack',
            auth_fn=auth_provider_stack.cognito_stack.cognito_auth_provider_function,
            auth_role_arn=auth_provider_stack.cognito_stack.authenticated_role_arn,
            parent_stack_name=self.stack_name,
            user_pool_client_id=auth_provider_stack.cognito_stack.user_pool_client.user_pool_client_id,
            user_pool_id=auth_provider_stack.cognito_stack.user_pool.user_pool_id,
            vpc=vpc_stack.vpc,
        )

        graph_store_provider_stack = GraphStoreProviderStack(self, 'GraphStoreProviderStack',
            app_security_group=vpc_stack.app_security_group,
            auth_fn=auth_provider_stack.cognito_stack.cognito_auth_provider_function,
            auth_role_arn=auth_provider_stack.cognito_stack.authenticated_role_arn,
            instance_type=self.node.try_get_context('neptune_instance_type'), # graph_provider_params['neptune_instance_type'],
            parent_stack_name=self.stack_name,
            user_pool_client_id=auth_provider_stack.cognito_stack.user_pool_client.user_pool_client_id,
            user_pool_id=auth_provider_stack.cognito_stack.user_pool.user_pool_id,
            vpc=vpc_stack.vpc
        )        

        enrichment_pipelines_handler_stack = EnrichmentPipelinesHandlerStack(self, "EnrichmentPipelinesHandlerStack",
            app_security_group=vpc_stack.app_security_group,
            auth_fn=auth_provider_stack.cognito_stack.cognito_auth_provider_function,
            parent_stack_name=self.stack_name,
            user_pool_client_id=auth_provider_stack.cognito_stack.user_pool_client.user_pool_client_id,
            user_pool_id=auth_provider_stack.cognito_stack.user_pool.user_pool_id,
            vpc=vpc_stack.vpc
        )
        
        generation_handler_stack = GenerationHandlerStack(self, 'GenerationHandlerApiStack',
            app_security_group=vpc_stack.app_security_group,
            auth_fn=auth_provider_stack.cognito_stack.cognito_auth_provider_function,
            auth_role_arn=auth_provider_stack.cognito_stack.authenticated_role_arn,
            parent_stack_name=self.stack_name,
            user_pool_client_id=auth_provider_stack.cognito_stack.user_pool_client.user_pool_client_id,
            user_pool_id=auth_provider_stack.cognito_stack.user_pool.user_pool_id,
            vpc=vpc_stack.vpc
        )

        FinalScriptsStack(self, 'FinalScriptsStack',
            bedrock_provider_function=bedrock_provider_stack.bedrock_provider_function,
            doc_collections_handler_function=doc_collections_stack.doc_collections_function,
            domain=vector_store_provider_stack.vector_store_stack.domain,
            embeddings_provider_function=embeddings_provider_stack.embeddings_provider_function,
            # enrichment_pipelines_handler_stack.entity_extraction_function.entity_extraction_function.grant_principal,
            extraction_function=enrichment_pipelines_handler_stack.entity_extraction_function.entity_extraction_function,
            graph_store_provider_function=graph_store_provider_stack.graph_store_provider,
            inference_principal=generation_handler_stack.generation_handler_function.grant_principal,
            ingestion_bucket=ingestion_provider_stack.ingestion_bucket.bucket,
            ingestion_function=ingestion_provider_stack.ingestion_function,
            # ingestion_principal=ingestion_provider_stack.ingestion_function.grant_principal,
            ingestion_queue=ingestion_provider_stack.ingestion_queue.queue,
            ingestion_status_provider_function=ingestion_provider_stack.ingestion_status_function,
            ingestion_status_table=ingestion_provider_stack.ingestion_status_table.table,
            prompt_templates_handler_function=prompt_templates_handler_stack.prompt_template_handler_function,
            vector_store_provider_function=vector_store_provider_stack.vector_store_stack.vector_store_provider,
        )

        # initialization_stack = InitializationHandlerStack(self, 
        #     'InitializationHandlerStack',
        #     auth_role_arn=cognito_stack.authenticated_role_arn,
        #     # system_settings_table=system_settings_table_stack.table,
        #     parent_stack_name=self.stack_name,
        #     user_pool_client_id=cognito_stack.user_pool_client.user_pool_client_id,
        #     user_pool_id=cognito_stack.user_pool.user_pool_id
        # )
        
        CfnOutput(self, 'AppName', value=self.node.get_context('app_name'))
        CfnOutput(self, 'RemovalPolicy', value=self.node.get_context('removal_policy'))
        CfnOutput(self, 'StackName', value=self.stack_name)
        CfnOutput(self, 'StackNameFrontend', value=self.node.try_get_context('stack_name_frontend'))


