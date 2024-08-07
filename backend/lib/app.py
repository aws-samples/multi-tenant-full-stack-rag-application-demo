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
    aws_s3 as s3
)

from constructs import Construct
from pathlib import Path

from .bucket import BucketStack
from .bucket_to_queue_event_trigger import BucketToQueueNotificationStack
from .__config__ import config
from .cognito import CognitoStack
from .document_collections import DocumentCollectionsStack
from .document_collections_http_api import DocumentCollectionsApiStack
from .dynamodb_table import DynamoDbTableStack
from .enrichment_pipelines.enrichment_pipelines_api import EnrichmentPipelinesApiStack
from .enrichment_pipelines.enrichment_pipelines_ssm_param import EnrichmentPipelinesSsmParamStack
from .enrichment_pipelines.entity_extraction import EntityExtractionPipelineStack
from .generation_handler_api import GenerationHandlerApiStack
from .initialization_handler_api import InitializationHandlerApiStack
from .neptune import NeptuneStack
from .opensearch_dashboards_proxy import OpenSearchDashboardsProxyStack
from .opensearch_managed import OpenSearchManagedStack
from .prompt_templates_api import PromptTemplatesStack
from .queue import QueueStack
from .queue_to_function_event_trigger import QueueToFunctionTriggerStack
from .rag_execution_roles import RagExecutionRolesStack
from .sharing_handler_api import SharingHandlerApiStack
from .sharing_post_confirmation_hook import SharingPostConfirmationHookStack
from .vector_ingestion import VectorIngestionStack
from .vpc import VpcStack


class MultiTenantRagStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vpc_stack = VpcStack(self, 'Vpc')

        ingestion_bucket_stack = BucketStack(self, 'IngestionBucketStack',
            resource_name='IngestionBucket',
            add_cors=True
        )

        ingestion_queue_stack = QueueStack(self, 'IngestionQueueStack', 
            resource_name='IngestionQueue',
            visibility_timeout=Duration.seconds(900)
        )

        ingestion_event_trigger = BucketToQueueNotificationStack(self, 'IngestionBucketToQueueTriggerStack', 
            bucket_name=ingestion_bucket_stack.bucket.bucket_name,
            queue=ingestion_queue_stack.queue,
            resource_name='IngestionEventTrigger'
        )

        ingestion_status_table_stack = DynamoDbTableStack(self, 'IngestionStatusTableStack',
            partition_key='user_id',
            partition_key_type=ddb.AttributeType.STRING,
            resource_name='IngestionStatusTable',
            vpc=vpc_stack.vpc,
            sort_key='s3_key',
            sort_key_type=ddb.AttributeType.STRING,
            create_stream=True
        )

        user_settings_table_stack = DynamoDbTableStack(self, 'UserSettingsTableStack',
            partition_key='user_id',
            partition_key_type=ddb.AttributeType.STRING,
            resource_name='UserSettingsTable',
            vpc=vpc_stack.vpc,
            sort_key='setting_name',
            sort_key_type=ddb.AttributeType.STRING,
            create_stream=True
        )

        system_settings_table_stack = DynamoDbTableStack(self, 'SystemSettingsTableStack',
            partition_key='id_key',
            partition_key_type=ddb.AttributeType.STRING,
            resource_name='SystemSettingsTable',
            vpc=vpc_stack.vpc,
            sort_key='sort_key',
            sort_key_type=ddb.AttributeType.STRING,
            create_stream=True
        )
        
        cognito_domain_prefix = f'{config["auth_provider_params"]["cognito"]["cognito_domain_prefix"]}-{self.account}-{self.region}'
        cognito_stack = CognitoStack(self, 'CognitoStack', 
            allowed_email_domains=config['auth_provider_params']["cognito"]['allowed_email_domains'],
            cognito_domain_prefix=cognito_domain_prefix,
            ingestion_bucket=ingestion_bucket_stack.bucket,
            # ingestion_status_table=ingestion_status_table_stack.table,
            system_settings_table=system_settings_table_stack.table,
            verification_message_body=config['auth_provider_params']['cognito']['verification_message_settings']['email_body'],
            verification_message_subject=config['auth_provider_params']['cognito']['verification_message_settings']['email_subject']
        )

        rag_execution_roles_stack = RagExecutionRolesStack(self, 'RagExecutionRolesStack')

        auth_provider = config['auth_provider']
        
        vector_store_stack = None
        vector_store_provider = config['vector_store_provider']
        vs_config = config['vector_store_provider_params'][vector_store_provider]

        if vector_store_provider == 'opensearch_managed':
            vector_store_stack = OpenSearchManagedStack(self, 'OpenSearchManagedDomainStack', 
                app_security_group=vpc_stack.app_security_group,
                cognito_auth_role=cognito_stack.identity_pool.authenticated_role,
                cognito_identity_pool_id=cognito_stack.identity_pool.identity_pool_id,
                cognito_user_pool_id=cognito_stack.user_pool.user_pool_id,
                inference_role_arn=rag_execution_roles_stack.inference_role.role_arn,
                ingestion_role_arn=rag_execution_roles_stack.ingestion_role.role_arn, 
                ingestion_status_table_name=ingestion_status_table_stack.table.table_name,
                os_data_instance_ct=vs_config['os_data_instance_ct'],
                os_data_instance_type=vs_config['os_data_instance_type'],
                os_master_instance_ct=vs_config['os_master_instance_ct'],
                os_master_instance_type=vs_config['os_master_instance_type'],
                os_multiaz_with_standby_enabled=vs_config['os_multiaz_with_standby_enabled'],
                vpc=vpc_stack.vpc,
            )
            vector_store_stack.add_dependency(vpc_stack)
            vector_store_stack.add_dependency(cognito_stack)
            vector_store_stack.add_dependency(rag_execution_roles_stack)

            opensearch_dashboards_proxy_stack = OpenSearchDashboardsProxyStack(self, 'OpenSearchDashboardsProxyStack',
                app_security_group=vpc_stack.app_security_group,
                ec2_cert_city=vs_config['ec2_cert_city'],
                ec2_cert_country=vs_config['ec2_cert_country'],
                ec2_cert_email=vs_config['ec2_cert_email_address'],
                ec2_cert_hostname=vs_config['ec2_cert_hostname'],
                ec2_cert_state=vs_config['ec2_cert_state'],
                ec2_enable_traffic_from_ip=vs_config['ec2_enable_traffic_from_ip'],
                os_domain=vector_store_stack.domain,
                user_pool_domain=cognito_stack.user_pool_domain,
                vpc=vpc_stack.vpc,
            )
        
        embeddings_provider = config['embeddings_provider']
        
        doc_collections_stack = DocumentCollectionsStack(self, 'DocumentCollectionsStack',
            allowed_email_domains=config['auth_provider_params'][auth_provider]['allowed_email_domains'],
            auth_role_arn=cognito_stack.authenticated_role_arn,
            auth_provider_args=cognito_stack.auth_provider_args,
            auth_provider_py_path=config['auth_provider_params'][auth_provider]['auth_provider_py_path'],
            cognito_identity_pool_id=cognito_stack.identity_pool.identity_pool_id,
            cognito_user_pool_id=cognito_stack.user_pool.user_pool_id,
            doc_collections_bucket=ingestion_bucket_stack.bucket,
            embeddings_provider_args=config['embeddings_provider_params'][embeddings_provider]['provider_args'],
            embeddings_provider_extra_env=config['embeddings_provider_params'][embeddings_provider]['extra_env'],
            embeddings_provider_py_path=config['embeddings_provider_params'][embeddings_provider]['py_path'],
            embeddings_provider_req_paths=config['embeddings_provider_params'][embeddings_provider]['requirements_paths'],
            ingestion_queue=ingestion_queue_stack.queue,
            ingestion_status_table=ingestion_status_table_stack.table,
            system_settings_table=system_settings_table_stack.table,
            user_settings_table=user_settings_table_stack.table,
            vector_store_domain=vector_store_stack.domain,
            vector_store_endpoint=vector_store_stack.vector_store_endpoint,
            vector_store_provider_py_path=vs_config['provider_py_path'],
            vector_store_req_paths=vs_config['requirements_paths'],
        )

        doc_collections_api_stack = DocumentCollectionsApiStack(
            self, 'DocumentCollectionsApiStack',
            doc_collections_function=doc_collections_stack.doc_collections_function,
            user_pool_client_id=cognito_stack.user_pool_client.user_pool_client_id,
            user_pool_id=cognito_stack.user_pool.user_pool_id,
        )
        
        graph_provider = config["graph_store_provider"]
        graph_provider_params = config["graph_store_provider_params"][graph_provider]

        neptune_stack = NeptuneStack(self, 'GraphProviderStack',
            app_security_group=vpc_stack.app_security_group,
            inference_role_arn=rag_execution_roles_stack.inference_role.role_arn,
            ingestion_role_arn=rag_execution_roles_stack.ingestion_role.role_arn,
            instance_type=graph_provider_params['neptune_instance_type'],
            vpc=vpc_stack.vpc
        )        
        
        entity_extraction_stack = EntityExtractionPipelineStack(self, 'EntityExtractionStack',
            app_security_group=vpc_stack.app_security_group,
            embeddings_provider_args=config['embeddings_provider_params'][embeddings_provider]['provider_args'],
            embeddings_provider_extra_env=config['embeddings_provider_params'][embeddings_provider]['extra_env'],
            embeddings_provider_iam_permissions=config['embeddings_provider_params'][embeddings_provider]['iam_permissions_needed'],
            embeddings_provider_py_path=config['embeddings_provider_params'][embeddings_provider]['py_path'],
            embeddings_provider_requirements_paths=config['embeddings_provider_params'][embeddings_provider]['requirements_paths'],
            extraction_model_id=config["enrichment_pipelines"]["entity_extraction"]["extraction_model_id"],
            ingestion_role=rag_execution_roles_stack.ingestion_role,
            ingestion_table=ingestion_status_table_stack.table,
            ingestion_table_stream=ingestion_status_table_stack.stream,
            neptune_endpoint=neptune_stack.cluster.cluster_endpoint.socket_address,
            req_paths=config['enrichment_pipelines']['entity_extraction']['requirements_paths'],
            system_settings_table=system_settings_table_stack.table,
            user_settings_table=user_settings_table_stack.table,
            vector_store_endpoint=vector_store_stack.vector_store_endpoint,
            vector_store_provider_py_path=vs_config['provider_py_path'],
            vector_store_requirements_paths=vs_config['requirements_paths'],
            vpc=vpc_stack.vpc
        )

        enrichment_pipelines_ssm_param_name = '/multitenantrag/enabled_enrichment_pipelines'

        enrichment_pipelines_ssm_param_stack = EnrichmentPipelinesSsmParamStack(self, 'EnrichmentPipelinesSsmParamStack',
            param_name=enrichment_pipelines_ssm_param_name,
            param_value=json.dumps({
                "entity_extraction": {
                    "name": "Entity Extraction"
                }
            })
        )

        enrichment_pipelines_api_stack = EnrichmentPipelinesApiStack(self, "EnrichmentPipelinesApiStack",
            auth_role_arn=cognito_stack.authenticated_role_arn,
            enrichment_pipelines_ssm_param=enrichment_pipelines_ssm_param_stack.ssm_param,
            user_pool_client_id=cognito_stack.user_pool_client.user_pool_client_id,
            user_pool_id=cognito_stack.user_pool.user_pool_id
        )

        vector_ingestion_stack = VectorIngestionStack(self, "VectorIngestionImgStack",
            allowed_email_domains=config['auth_provider_params'][auth_provider]['allowed_email_domains'],
            app_security_group=vpc_stack.app_security_group,
            auth_provider_args=cognito_stack.auth_provider_args,
            cognito_identity_pool_id=cognito_stack.identity_pool.identity_pool_id,
            cognito_user_pool_id=cognito_stack.user_pool.user_pool_id,
            document_collections_bucket=ingestion_bucket_stack.bucket,
            embeddings_provider_args=config['embeddings_provider_params'][embeddings_provider]['provider_args'],
            embeddings_provider_extra_env=config['embeddings_provider_params'][embeddings_provider]['extra_env'],
            embeddings_provider_iam_permissions=config['embeddings_provider_params'][embeddings_provider]['iam_permissions_needed'],
            embeddings_provider_py_path=config['embeddings_provider_params'][embeddings_provider]['py_path'],
            embeddings_provider_requirements_paths=config['embeddings_provider_params'][embeddings_provider]['requirements_paths'],
            ingestion_role=rag_execution_roles_stack.ingestion_role,
            ingestion_status_table=ingestion_status_table_stack.table,
            ocr_model_id=config["vector_store_provider_params"]["loader_params"]["PdfImageLoader"]["default_ocr_model"],
            system_settings_table=system_settings_table_stack.table,
            user_settings_table=user_settings_table_stack.table,
            vector_store_endpoint=vector_store_stack.vector_store_endpoint,
            vector_store_provider_py_path=vs_config['provider_py_path'],
            vector_store_requirements_paths=vs_config['requirements_paths'],
            vpc=vpc_stack.vpc
        )

        queue_to_function_trigger_stack = QueueToFunctionTriggerStack(self, 'QueueToFunctionTriggerStack',
            function=vector_ingestion_stack.ingestion_function,
            queue_arn=ingestion_queue_stack.queue.queue_arn,
            resource_name='IngestionQueueToFunctionTrigger'
        )
        
        gen_handler = config["generation_handler"]

        generation_handler_stack = GenerationHandlerApiStack(self, 'GenerationHandlerApiStack',
            allowed_email_domains=config['auth_provider_params'][auth_provider]['allowed_email_domains'],
            auth_provider_py_path=config['auth_provider_params'][auth_provider]['auth_provider_py_path'],
            auth_role_arn=cognito_stack.authenticated_role_arn,
            cognito_identity_pool_id=cognito_stack.identity_pool.identity_pool_id,
            cognito_user_pool_id=cognito_stack.user_pool.user_pool_id,
            embeddings_provider_args=config['embeddings_provider_params'][embeddings_provider]['provider_args'],
            embeddings_provider_extra_env=config['embeddings_provider_params'][embeddings_provider]['extra_env'],
            embeddings_provider_py_path=config['embeddings_provider_params'][embeddings_provider]['py_path'],
            embeddings_provider_req_paths=config['embeddings_provider_params'][embeddings_provider]['requirements_paths'],
            inference_role=rag_execution_roles_stack.inference_role,
            ingestion_status_table=ingestion_status_table_stack.table,
            neptune_endpoint=neptune_stack.cluster.cluster_endpoint.socket_address,
            system_settings_table=system_settings_table_stack.table,
            user_settings_table=user_settings_table_stack.table,
            req_paths=config["generation_handler_params"][gen_handler]["requirements_paths"],
            user_pool_client_id=cognito_stack.user_pool_client.user_pool_client_id,
            user_pool_id=cognito_stack.user_pool.user_pool_id,
            vector_store_endpoint=vector_store_stack.vector_store_endpoint,
            vector_store_provider_py_path=vs_config['provider_py_path'],
            vector_store_req_paths=vs_config['requirements_paths'],
            vpc=vpc_stack.vpc
        )

        prompt_templates_stack = PromptTemplatesStack(self, 'PromptTemplatesStack',
            cognito_auth_role_arn=cognito_stack.authenticated_role_arn,
            identity_pool_id=cognito_stack.identity_pool.identity_pool_id,
            user_pool_client_id=cognito_stack.user_pool_client.user_pool_client_id,
            user_pool_id=cognito_stack.user_pool.user_pool_id,
            user_settings_table=user_settings_table_stack.table,
        )

        sharing_handler_stack = SharingHandlerApiStack(self, 
            'SharingHandlerApiStack',
            allowed_email_domains=config['auth_provider_params'][auth_provider]['allowed_email_domains'],
            auth_role_arn=cognito_stack.authenticated_role_arn,
            embeddings_provider_args=config['embeddings_provider_params'][embeddings_provider]['provider_args'],
            embeddings_provider_extra_env=config['embeddings_provider_params'][embeddings_provider]['extra_env'],
            embeddings_provider_py_path=config['embeddings_provider_params'][embeddings_provider]['py_path'],
            embeddings_provider_req_paths=config['embeddings_provider_params'][embeddings_provider]['requirements_paths'],
            ingestion_status_table=ingestion_status_table_stack.table,
            system_settings_table=system_settings_table_stack.table,
            system_settings_table_stream=system_settings_table_stack.stream,
            user_pool_client_id=cognito_stack.user_pool_client.user_pool_client_id,
            user_pool_id=cognito_stack.user_pool.user_pool_id,
            user_settings_table=user_settings_table_stack.table,
            user_settings_table_stream=user_settings_table_stack.stream,
            vector_store_endpoint=vector_store_stack.vector_store_endpoint,
            vector_store_provider_py_path=vs_config['provider_py_path'],
            vector_store_req_paths=vs_config['requirements_paths'],
            vpc=vpc_stack.vpc
        )

        initialization_stack = InitializationHandlerApiStack(self, 
            'InitializationHandlerStack',
            auth_role_arn=cognito_stack.authenticated_role_arn,
            system_settings_table=system_settings_table_stack.table,
            user_pool_client_id=cognito_stack.user_pool_client.user_pool_client_id,
            user_pool_id=cognito_stack.user_pool.user_pool_id
        )

