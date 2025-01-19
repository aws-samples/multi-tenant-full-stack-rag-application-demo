#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0
#!/bin/bash
export PYTHONPATH=../src:$PYTHONPATH
export ENV_CONFIG=`cat ../../frontend/backend_outputs.json`
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment"
    python3 -m venv .venv
    echo "Installing dependencies"
    source .venv/bin/activate
    pip3 install --upgrade pip
    pip3 install pytest pytest-cov
    pip3 install pytest
fi
source .venv/bin/activate &&
# pip3 install aws-requests-auth
# pip3 uninstall pytest-socket
# pip3 uninstall moto[all] &&
# pip3 install --no-cache-dir -U  moto[all] &&
# pip3 install --no-cache -r ../requirements.txt &&
# pip3 install --no-cache -r ../src/multi_tenant_full_stack_rag_application/enrichment_pipelines/entity_extraction/entity_extraction_requirements.txt && 
# pip3 install --no-cache -r ../src/multi_tenant_full_stack_rag_application/bedrock_provider/bedrock_provider_requirements.txt &&
# pip3 install --no-cache -r ../src/multi_tenant_full_stack_rag_application/sharing_handler/user_settings_stream_processor_requirements.txt &&
# pip3 install --no-cache -r ../src/multi_tenant_full_stack_rag_application/sharing_handler/sharing_handler_requirements.txt &&
# pip3 install --no-cache -r ../src/multi_tenant_full_stack_rag_application/sharing_handler/system_settings_stream_processor_requirements.txt &&
# pip3 install --no-cache -r ../src/multi_tenant_full_stack_rag_application/embeddings_provider/bedrock_embeddings_provider_requirements.txt &&
# pip3 install --no-cache -r ../src/multi_tenant_full_stack_rag_application/generation_handler/generation_handler_requirements.txt &&
# pip3 install --no-cache -r ../src/multi_tenant_full_stack_rag_application/vector_store_provider/vector_ingestion_requirements.txt &&
# pip3 install --no-cache -r ../src/multi_tenant_full_stack_rag_application/vector_store_provider/loaders/pdf_image_loader_requirements.txt &&
# pip3 install --no-cache -r ../src/multi_tenant_full_stack_rag_application/vector_store_provider/loaders/loader_requirements.txt &&
# # pip3 install --no-cache -r ../src/multi_tenant_full_stack_rag_application/vector_store_provider/loaders/tabular_data_loader_requirements.txt &&
# pip3 install --no-cache -r ../src/multi_tenant_full_stack_rag_application/vector_store_provider/loaders/docx_loader_requirements.txt &&
# pip3 install --no-cache -r ../src/multi_tenant_full_stack_rag_application/vector_store_provider/opensearch_requirements.txt &&
# pip3 install --no-cache -r ../src/multi_tenant_full_stack_rag_application/initialization_handler/initialization_handler_requirements.txt &&
# pip3 install --no-cache -r ../src/multi_tenant_full_stack_rag_application/system_settings_provider/system_settings_provider_requirements.txt &&
. env.sh  &&
echo STACK_NAME = $STACK_NAME

python3 -m pytest --cov=multi_tenant_full_stack_rag_application -x -s multi_tenant_full_stack_rag_application 
    # --ignore=multi_tenant_full_stack_rag_application/generation_handler \
    # --ignore=multi_tenant_full_stack_rag_application/enrichment_pipelines_provider \
    #  --ignore=multi_tenant_full_stack_rag_application/embeddings_provider 
    # --ignore=multi_tenant_full_stack_rag_application/utils 
    # --ignore=multi_tenant_full_stack_rag_application/bedrock_provider \
    # --ignore=multi_tenant_full_stack_rag_application/document_collections_handler \
    # --ignore=multi_tenant_full_stack_rag_application/ingestion_provider \
    # --ignore=multi_tenant_full_stack_rag_application/vector_store_provider \


    
    
