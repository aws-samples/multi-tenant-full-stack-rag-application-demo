#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import os
from aws_cdk import aws_neptune_alpha as neptune

region = os.getenv('AWS_REGION')
bedrock_emb_model = 'amazon.titan-embed-text-v2:0'
app_name = 'Multi-tenant full-stack RAG demo'

config = {
   "auth_provider": "cognito",
   "auth_provider_params": {
      "cognito": {
         # use "*" for an allowed email domain to allow all.
         # that will override any other values. Don't use @ or 
         # asterisks in the email domain name. The value
         # provided will be used in its entirety after the @ sign.
         "allowed_email_domains": ["amazon.com"],
         # The account id and region will be appended to the cognito domain prefix later,
         # so it won't collide with your other accounts and regions later. The resulting
         # cognito domain must result in a globally unique DNS prefix across all of AWS.
         "cognito_domain_prefix": "multi-tenant-rag-demo",
         "auth_provider_py_path": "multi_tenant_full_stack_rag_application.auth_provider.cognito_auth_provider.CognitoAuthProvider",
         "auth_provider_args": [],
         "verification_message_settings": {
            "email_subject": f"Verify your email for {app_name}",
            "email_body": f"Thanks for signing up {app_name}! Your verification code is {{####}}"
         }
      }
   },
   "embeddings_provider": "bedrock",
   "embeddings_provider_params": {
      "bedrock": {
         "extra_env": {
            "HUGGINGFACE_HUB_CACHE": "/tmp",
            "TRANSFORMERS_CACHE": '/tmp'
         },
         "iam_permissions_needed": [{
            "actions": [
               "bedrock:InvokeModel"
            ],
            "resources": [
               f"arn:aws:bedrock:{region}::foundation-model/{bedrock_emb_model}"
            ]
         }],
         "requirements_paths": [
            # relative to the src/multi_tenant_full_stack_rag_application parent folder
            "embeddings_provider/bedrock_embeddings_provider_requirements.txt",
            "bedrock_provider/bedrock_provider_requirements.txt"
         ],
         "provider_args": [
            bedrock_emb_model
         ],
         # relative to the src/ folder.
         "py_path": "multi_tenant_full_stack_rag_application.embeddings_provider.bedrock_embeddings_provider.BedrockEmbeddingsProvider"
      }
   },
   "enrichment_pipelines": {
      "entity_extraction": {
         "name": "Entity Extraction Pipeline",
         "py_path": 'multi_tenant_full_stack_rag_application.enrichment_pipelines.EntityExtraction',
         "requirements_paths": [
            "enrichment_pipelines/entity_extraction/entity_extraction_requirements.txt",
            "bedrock_provider/bedrock_provider_requirements.txt"
         ],
         "extraction_model_id": "anthropic.claude-3-haiku-20240307-v1:0",
         # "extraction_model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
      }
   },
   "generation_handler": "bedrock",
   "generation_handler_params": {
      "bedrock": {
         "provider_args": {},
         "py_path": 'multi_tenant_full_stack_rag_application.generation_handler.GenerationHandler',
         "requirements_paths": [
            "generation_handler/generation_handler_requirements.txt",
            "bedrock_provider/bedrock_provider_requirements.txt"
         ],
      }
   },
   "graph_store_provider": "neptune",
   "graph_store_provider_params": { 
      "neptune": {
         "neptune_instance_type": neptune.InstanceType.T4_G_MEDIUM
      }
   },
   "vector_store_provider": "opensearch_managed",
   "vector_store_provider_params": {
      "loader_params": {
         "PdfImageLoader": {
            "default_ocr_model": "anthropic.claude-3-haiku-20240307-v1:0"
         }
      },
      "opensearch_managed": {
         "os_data_instance_ct": 2,
         "os_data_instance_type": "t3.small.search",
         "os_master_instance_ct": 0,
         "os_master_instance_type": '',
         "os_multiaz_with_standby_enabled": False,
         # these cert params are for the opensearch dashboards
         # proxy ec2 instance
         "ec2_cert_country": 'US',
         "ec2_cert_state": 'California',
         "ec2_cert_city": 'Irvine',
         "ec2_cert_hostname": 'ossdashboard-proxy.mydomain.com',
         "ec2_cert_email_address": 'someuser@someexampledomain8h01h.com',
         # use ec2_enable_traffic_from_ip and add your IP, and it will be added for HTTPS access
         # to the OpenSearch Dashboards proxy. If you leave it commented, nobody
         # will be able to connect to that machine. Changing this and rerunning the
         # stack will not impact any data, but may result in a change of IP on the
         # proxy machine and an interruption in service to spin up a new t4g.nano
         # machine with the new configuration. Alternatively, you can add your 
         # own IP to the security group later, via the console. You can replace this
         # with any single CIDR, for now. Otherwise add your IP CIDR(s) via the console
         # or edit the CDK code to handle a list here.
         "ec2_enable_traffic_from_ip": '127.0.0.1/32',     
         "provider_py_path": "multi_tenant_full_stack_rag_application.vector_store_provider.opensearch_vector_store_provider.OpenSearchVectorStoreProvider",
         "requirements_paths": [
            "vector_store_provider/opensearch_requirements.txt"
         ]
      }
   }
}
