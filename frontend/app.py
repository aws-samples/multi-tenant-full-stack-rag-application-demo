#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import glob
import json
import os
import shutil
import yaml

from aws_cdk import App, DefaultStackSynthesizer
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

if not os.path.isdir('src/multi_tenant_full_stack_rag_application/ui/src/commons/prompt_templates'):
    os.mkdir('src/multi_tenant_full_stack_rag_application/ui/src/commons/prompt_templates')

shutil.copyfile(
    '../backend/src/multi_tenant_full_stack_rag_application/bedrock_provider/bedrock_model_params.json', 
    'src/multi_tenant_full_stack_rag_application/ui/src/commons/bedrock_model_params.json'
)

with open('src/multi_tenant_full_stack_rag_application/ui/src/commons/bedrock_model_params.json', 'r') as f_in:
    bedrock_model_params = json.loads(f_in.read())
    bedrock_model_ids = list(bedrock_model_params.keys())


for model_id in bedrock_model_ids:
    if region == 'us-west-2'and model_id.startswith('amazon.nova'):
        model_dict = bedrock_model_params[model_id]
        new_model_id = f"us.{model_id}"
        bedrock_model_params[new_model_id] = model_dict
        del bedrock_model_params[model_id]

with open('src/multi_tenant_full_stack_rag_application/ui/src/commons/bedrock_model_params.json', 'w') as f_out:
    f_out.write(json.dumps(bedrock_model_params))

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

# app_name = 'AWS Generative AI Accelerator'

with open('../backend/cdk.context.json', 'r') as f_in:
    cdk_context = json.loads(f_in.read())
    # for key in list(cdk_context.keys()):
    #     if key == 'app_name':
    #         app_name = cdk_context[key]

# with open('../backend/lib/__config__.py', 'r') as f_in:
#     lines = f_in.readlines()
#     for line in lines:
#         if line.strip().startswith('app_name'):
#             app_name = line.split("=")[1].strip().strip("'").strip('"').strip()

with open('backend_outputs.json', 'r') as backend_outputs:
    config_in = json.loads(backend_outputs.read())
    for key in list(config_in.keys()):
        if 'DocumentCollections' in key:
            for subkey in list(config_in[key].keys()):
                if subkey == 'HttpApiUrl':
                    config['document_collections_api_url'] = config_in[key][subkey].rstrip('/')
                    break
        elif 'EnrichmentPipelines' in key:
            config['enabled_enrichment_pipelines'] = config_in[key]['EnabledEnrichmentPipelines']
        elif 'GenerationHandler' in key:
            for subkey in list(config_in[key].keys()):
                if subkey == 'GenerationHandlerHttpApiUrl':
                    config['generation_api_url'] = config_in[key][subkey].rstrip('/')
                    break
        elif 'AuthProviderStack' in key:
            for subkey in list(config_in[key].keys()):
                if subkey == "UserPoolClientId":
                    config["user_pool_client_id"] = config_in[key][subkey]
                elif subkey == "UserPoolId":
                    config["user_pool_id"] = config_in[key][subkey]
                elif subkey == 'IdentityPoolId':
                    config["identity_pool_id"] = config_in[key][subkey]
        elif 'IngestionProviderStack' in key:
            for subkey in list(config_in[key].keys()):
                if subkey == 'IngestionBucketName':
                    config["ingestion_bucket_name"] = config_in[key][subkey]
        elif 'PromptTemplateHandlerStack' in key:
            for subkey in list(config_in[key].keys()):
                if subkey == 'PromptTemplateHandlerApiUrl':
                    config["prompt_templates_api_url"] = config_in[key][subkey].rstrip('/')
        else:
            config_item = config_in[key]
            for subkey in config_item:
                if subkey == 'AppName': 
                    config['app_name'] = config_in[key][subkey]
                if subkey == 'RemovalPolicy': 
                    config['removal_policy'] = config_in[key][subkey]
                if subkey == 'StackName':
                    config["stack_name_backend"] = config_item[subkey]
                if subkey == 'StackNameFrontend':
                    config["stack_name_frontend"] = config_in[key][subkey]

ReactUiStack(app,  config['stack_name_frontend'],
    app_name=config['app_name'],
    doc_collections_api_url=config["document_collections_api_url"],
    enabled_enrichment_pipelines=config["enabled_enrichment_pipelines"],
    generation_api_url=config["generation_api_url"],
    identity_pool_id=config['identity_pool_id'],
    ingestion_bucket_name=config['ingestion_bucket_name'],
    # initialization_api_url=config['initialization_api_url'],
    prompt_templates_api_url=config['prompt_templates_api_url'],
    region=region,
    removal_policy=config['removal_policy'],
    stack_name_backend=config['stack_name_backend'],
    stack_name_frontend=config['stack_name_frontend'],
    # sharing_handler_api_url=config['sharing_handler_api_url'],
    user_pool_id=config["user_pool_id"],
    user_pool_client_id=config["user_pool_client_id"],
    synthesizer=DefaultStackSynthesizer(
        generate_bootstrap_version_rule=False
    ),
)

app.synth()
