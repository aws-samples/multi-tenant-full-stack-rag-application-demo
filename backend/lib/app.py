#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json
import os
import yaml

from aws_cdk import (
    CfnOutput,
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

        vpc_stack = VpcStack(self, 'Vpc')

        allowed_email_domains = []
        allowed_email_domains_csv = self.node.try_get_context('allowed_email_domains')
        for email_domain in allowed_email_domains_csv.split(','):
            allowed_email_domains.append(email_domain.strip())

        auth_provider_stack = AuthProviderStack(self, 'AuthProviderStack', 
            allowed_email_domains=allowed_email_domains,
            app_security_group=vpc_stack.app_security_group,
            parent_stack_name=self.stack_name,
            verification_message_body=self.node.try_get_context('verification_email_body'),
            verification_message_subject=self.node.try_get_context('verification_email_subject'),
            vpc=vpc_stack.vpc,
        )
        
        bedrock_provider_stack = BedrockProviderStack(self, 'BedrockProviderStack',
            user_pool_client_id=auth_provider_stack.cognito_stack.user_pool_client.user_pool_client_id,
            user_pool_id=auth_provider_stack.cognito_stack.user_pool.user_pool_id,
            parent_stack_name=self.stack_name,
            vpc=vpc_stack.vpc
        )

        embeddings_provider_stack = EmbeddingsProviderStack(
            self, 'EmbeddingsProviderStack',
            embeddings_model_id=self.node.try_get_context('embeddings_model_id'),
            parent_stack_name=self.stack_name,
            user_pool_client_id=auth_provider_stack.cognito_stack.user_pool_client.user_pool_client_id,
            user_pool_id=auth_provider_stack.cognito_stack.user_pool.user_pool_id,
            vpc=vpc_stack.vpc,
        )
        
        # system_settings_provider_stack = SystemSettingsProviderStack(self, 'SystemSettingsProviderStack',
        #     parent_stack_name=self.stack_name,
        #     vpc=vpc_stack.vpc
        # )

        ingestion_provider_stack = IngestionProviderStack(self, 'IngestionProviderStack',
            app_security_group=vpc_stack.app_security_group,
            parent_stack_name=self.stack_name,
            user_pool_client_id=auth_provider_stack.cognito_stack.user_pool_client.user_pool_client_id,
            user_pool_id=auth_provider_stack.cognito_stack.user_pool.user_pool_id,
            vpc=vpc_stack.vpc
        )

        # user_settings_provider_stack = UserSettingsProviderStack(self, 'UserSettingsProviderStack',
        #     parent_stack_name=self.stack_name,
        #     vpc=vpc_stack.vpc
        # )

        vector_store_provider_stack = VectorStoreProviderStack(self, 'VectorStoreProviderStack',
            app_security_group=vpc_stack.app_security_group,
            cognito_identity_pool=auth_provider_stack.cognito_stack.identity_pool,
            cognito_user_pool=auth_provider_stack.cognito_stack.user_pool,
            parent_stack_name=self.stack_name,
            user_pool_client_id=auth_provider_stack.cognito_stack.user_pool_client.user_pool_client_id,
            user_pool_domain=auth_provider_stack.cognito_stack.user_pool_domain,
            user_pool_id=auth_provider_stack.cognito_stack.user_pool.user_pool_id,
            vpc=vpc_stack.vpc
        )

        # final_scripts_hook = FinalScriptsStack(self, 'FinalScriptsStack',
        #     domain=vector_store_provider_stack.vector_store_stack.domain,
        #     ingestion_role=ingestion_provider_stack.ingestion_role
        # )
        
        doc_collections_stack = DocumentCollectionsHandlerStack(self, 'DocumentCollectionsHandlerStack',
            auth_role_arn=auth_provider_stack.cognito_stack.authenticated_role_arn,
            cognito_identity_pool_id=auth_provider_stack.cognito_stack.identity_pool.identity_pool_id,
            cognito_user_pool_client_id=auth_provider_stack.cognito_stack.user_pool_client.user_pool_client_id,
            cognito_user_pool_id=auth_provider_stack.cognito_stack.user_pool.user_pool_id,
            parent_stack_name=self.stack_name,            
            vpc=vpc_stack.vpc
        )

        prompt_templates_handler_stack = PromptTemplateHandlerStack(self, 'PromptTemplateHandlerStack',
            auth_role_arn=auth_provider_stack.cognito_stack.authenticated_role_arn,
            parent_stack_name=self.stack_name,
            user_pool_client_id=auth_provider_stack.cognito_stack.user_pool_client.user_pool_client_id,
            user_pool_id=auth_provider_stack.cognito_stack.user_pool.user_pool_id,
            vpc=vpc_stack.vpc,
        )

        graph_store_provider_stack = GraphStoreProviderStack(self, 'GraphStoreProviderStack',
            app_security_group=vpc_stack.app_security_group,
            auth_role_arn=auth_provider_stack.cognito_stack.authenticated_role_arn,
            instance_type=self.node.try_get_context('neptune_instance_type'), # graph_provider_params['neptune_instance_type'],
            parent_stack_name=self.stack_name,
            user_pool_client_id=auth_provider_stack.cognito_stack.user_pool_client.user_pool_client_id,
            user_pool_id=auth_provider_stack.cognito_stack.user_pool.user_pool_id,
            vpc=vpc_stack.vpc
        )        

        enrichment_pipelines_handler_stack = EnrichmentPipelinesHandlerStack(self, "EnrichmentPipelinesHandlerStack",
            app_security_group=vpc_stack.app_security_group,
            auth_role_arn=auth_provider_stack.cognito_stack.authenticated_role_arn,
            parent_stack_name=self.stack_name,
            user_pool_client_id=auth_provider_stack.cognito_stack.user_pool_client.user_pool_client_id,
            user_pool_id=auth_provider_stack.cognito_stack.user_pool.user_pool_id,
            vpc=vpc_stack.vpc
        )
        
        generation_handler_stack = GenerationHandlerStack(self, 'GenerationHandlerApiStack',
            auth_role_arn=auth_provider_stack.cognito_stack.authenticated_role_arn,
            parent_stack_name=self.stack_name,
            user_pool_client_id=auth_provider_stack.cognito_stack.user_pool_client.user_pool_client_id,
            user_pool_id=auth_provider_stack.cognito_stack.user_pool.user_pool_id,
            vpc=vpc_stack.vpc
        )

        # sharing_handler_stack = SharingHandlerStack(self, 
        #     'SharingHandlerApiStack',
        #     auth_role_arn=auth_provider_stack.cognito_stack.authenticated_role_arn,
        #     parent_stack_name=self.stack_name,
        #     user_pool_client_id=auth_provider_stack.cognito_stack.user_pool_client.user_pool_client_id,
        #     user_pool_id=auth_provider_stack.cognito_stack.user_pool.user_pool_id,
        #     vpc=vpc_stack.vpc
        # )

        # initialization_stack = InitializationHandlerStack(self, 
        #     'InitializationHandlerStack',
        #     auth_role_arn=cognito_stack.authenticated_role_arn,
        #     # system_settings_table=system_settings_table_stack.table,
        #     parent_stack_name=self.stack_name,
        #     user_pool_client_id=cognito_stack.user_pool_client.user_pool_client_id,
        #     user_pool_id=cognito_stack.user_pool.user_pool_id
        # )

        # # # the goal of doing all the final permission assignments at the end is to 
        # # # decouple the most of the stack to run in parallel.
        # # final_permissions_assignments = FinalPermissionAssignments(self, 
        # #     'FinalPermissionsAssignments',
        # #     cognito_auth_role_arn=cognito_stack.identity_pool.authenticated_role.role_arn,
        # #     ingestion_bucket=ingestion_bucket_stack.bucket,
        # #     doc_collections_function=doc_collections_stack.doc_collections_function,
        # #     embeddings_provider_iam_permissions=config['embeddings_provider_params'][embeddings_provider]['iam_permissions_needed'],
        # #     enrichment_pipelines_handler=enrichment_pipelines_api_stack.enrichment_pipelines_handler,
        # #     entity_extraction_function=entity_extraction_stack.entity_extraction_function,
        # #     generation_handler_function=generation_handler_stack.generation_handler_function,
        # #     inference_role=rag_execution_roles_stack.inference_role,
        # #     ingestion_function=vector_ingestion_stack.ingestion_function,
        # #     ingestion_queue_arn=ingestion_queue_stack.queue.queue_arn,
        # #     ingestion_role=rag_execution_roles_stack.ingestion_role,
        # #     ingestion_status_table=ingestion_status_table_stack.table,
        # #     initialization_handler_function=initialization_stack.initialization_handler_function,
        # #     neptune_cluster=neptune_stack.cluster,
        # #     os_managed_domain=vector_store_stack.domain,
        # #     parent_stack_name=self.stack_name,
        # #     post_confirmation_trigger_function=cognito_stack.post_confirmation_trigger,
        # #     prompt_templates_handler_function=prompt_templates_stack.prompt_templates_handler_function,
        # #     sharing_handler_function=sharing_handler_stack.sharing_function,
        # #     system_settings_stream_processor=sharing_handler_stack.system_settings_stream_processor,
        # #     system_settings_table=system_settings_table_stack.table,
        # #     user_settings_stream_processor=sharing_handler_stack.user_settings_stream_processor,
        # #     user_settings_table=user_settings_table_stack.table,
        # #     vector_ingestion_function=vector_ingestion_stack.ingestion_function,
        # # )
        CfnOutput(self, 'StackName', value=self.stack_name)
        # # CfnOutput(self, 'DocumentCollectionsApiUrl', value=doc_collections_api_stack.http_api.url)
        # # CfnOutput(self, 'DocumentCollectionsBucketName', value=ingestion_bucket_stack.bucket.bucket_name)
        # # CfnOutput(self, 'EnrichmentPipelinesApiUrl', value=enrichment_pipelines_api_stack.http_api.url)
        # # CfnOutput(self, 'GenerationApiUrl', value=generation_handler_stack.http_api.url)
        # # CfnOutput(self, 'IdentityPoolId', value=cognito_stack.identity_pool.identity_pool_id)
        # # CfnOutput(self, 'InitializationApiUrl', value=initialization_stack.http_api.url)
        # # CfnOutput(self, 'PromptTemplatesApiUrl', value=prompt_templates_stack.http_api.url)
        # # CfnOutput(self, 'SharingApiUrl', value=sharing_handler_stack.http_api.url)
        # # CfnOutput(self, 'UserPoolClientId', value=cognito_stack.user_pool_client.user_pool_client_id)
        # # CfnOutput(self, 'UserPoolId', value=cognito_stack.user_pool.user_pool_id)


