#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import glob
import json
import os
import shutil
import yaml

from aws_cdk import App
from lib.react_ui import ReactUiStack
from pathlib import Path

app = App()

account = os.getenv(
    'AWS_ACCOUNT_ID', 
    os.getenv('CDK_DEFAULT_ACCOUNT', '')
)
acct_pref = account[:6]

region = os.getenv(
    'AWS_REGION', 
    os.getenv('CDK_DEFAULT_REGION','')
)

config = {}

shutil.copyfile(
    '../backend/src/multi_tenant_full_stack_rag_application/bedrock_provider/bedrock_model_params.json', 
    'src/multi_tenant_full_stack_rag_application/ui/src/commons/bedrock_model_params.json'
)

if not os.path.isdir('src/multi_tenant_full_stack_rag_application/ui/src/commons/prompt_templates'):
    os.mkdir('src/multi_tenant_full_stack_rag_application/ui/src/commons/prompt_templates')

with open('src/multi_tenant_full_stack_rag_application/ui/src/commons/bedrock_model_params.json', 'r') as f_in:
    bedrock_model_params = json.loads(f_in.read())
    bedrock_model_ids = list(bedrock_model_params.keys())

templates = {}
for file in glob.glob(
    '../backend/src/multi_tenant_full_stack_rag_application/prompt_template_handler/prompt_templates/default*.txt'
):
    template_name = file.split('/')[-1].split('.')[0]
    search_key = template_name.split('_')[1]

    model_ids = []
    for model_id in bedrock_model_ids:
        if search_key in model_id:
            model_ids.append(model_id)

    templates[template_name] = {
        "template_id": template_name,
        "template_name": template_name,
        "template_text": Path(file).read_text(),
        "model_ids": model_ids,
        "stop_sequences": []
    }

with open('src/multi_tenant_full_stack_rag_application/ui/src/commons/prompt_templates/prompt_templates.json', 'w') as prompt_templates:
    prompt_templates.write(json.dumps(templates))

app_name = 'AWS Generative AI Accelerator'

with open('../backend/lib/__config__.py', 'r') as f_in:
    lines = f_in.readlines()
    for line in lines:
        if line.strip().startswith('app_name'):
            app_name = line.split("=")[1].strip().strip("'").strip('"').strip()
    
with open('backend_outputs.json', 'r') as backend_outputs:
    config_in = json.loads(backend_outputs.read())
    for key in list(config_in.keys()):
        if 'DocumentCollectionsApi' in key:
            for subkey in list(config_in[key].keys()):
                if subkey == 'HttpApiUrl':
                    config['document_collections_api_url'] = config_in[key][subkey].rstrip('/')
                    break
        elif 'EnrichmentPipelinesApi' in key:
            config['enrichment_pipelines_api_url'] = config_in[key]['EnrichmentPipelinesHttpApiUrl'].rstrip('/')
        elif 'GenerationHandlerApi' in key:
            for subkey in list(config_in[key].keys()):
                if subkey == 'GenerationHandlerHttpApiUrl':
                    config['generation_api_url'] = config_in[key][subkey].rstrip('/')
                    break
        elif 'CognitoStack' in key:
            for subkey in list(config_in[key].keys()):
                if subkey == "UserPoolClientId":
                    config["user_pool_client_id"] = config_in[key][subkey]
                elif subkey == "UserPoolId":
                    config["user_pool_id"] = config_in[key][subkey]
                elif subkey == 'IdentityPoolId':
                    config["identity_pool_id"] = config_in[key][subkey]
        elif 'IngestionBucketStack' in key:
            for subkey in list(config_in[key].keys()):
                if subkey == 'IngestionBucketBucketName':
                    config["doc_collections_bucket_name"] = config_in[key][subkey]
        elif 'PromptTemplatesStack' in key:
            for subkey in list(config_in[key].keys()):
                if subkey == 'PromptTemplatesHttpApiUrl':
                    config["prompt_templates_api_url"] = config_in[key][subkey].rstrip('/')
        elif 'SharingHandler' in key:
            for subkey in list(config_in[key].keys()):
                if subkey == 'SharingHandlerHttpApiUrl':
                    config["sharing_handler_api_url"] = config_in[key][subkey].rstrip('/')
        elif 'InitializationHandler' in key:
            for subkey in list(config_in[key].keys()):
                if subkey == 'InitializationHandlerHttpApiUrl':
                    config["initialization_api_url"] = config_in[key][subkey].rstrip('/')


ReactUiStack(app, "MultiTenantRagUiStack",
    app_name=app_name,
    doc_collections_bucket_name=config['doc_collections_bucket_name'],
    doc_collections_api_url=config["document_collections_api_url"],
    enrichment_pipelines_api_url=config["enrichment_pipelines_api_url"],
    generation_api_url=config["generation_api_url"],
    identity_pool_id=config['identity_pool_id'],
    initialization_api_url=config['initialization_api_url'],
    prompt_templates_api_url=config['prompt_templates_api_url'],
    region=region,
    sharing_handler_api_url=config['sharing_handler_api_url'],
    user_pool_id=config["user_pool_id"],
    user_pool_client_id=config["user_pool_client_id"],
)

app.synth()
