#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0
#!/bin/bash
export PYTHONPATH=../src:$PYTHONPATH
export ENV_CONFIG=`cat ../../frontend/backend_outputs.json`
if [ ! -d "../../.venv" ]; then
    echo "Creating virtual environment"
    uv venv ../../.venv
fi
echo "Installing dependencies" && 
source ../../.venv/bin/activate && 
source .env
uv pip install --upgrade pip && 
uv pip install pytest pytest-cov moto aws_requests_auth && 
uv pip install -r ../requirements.txt && 
uv pip install -r ../src/multi_tenant_full_stack_rag_application/vector_store_provider/opensearch_requirements.txt && 
uv pip install -r ../src/multi_tenant_full_stack_rag_application/generation_handler/generation_handler_requirements.txt && 
uv pip install -r ../src/multi_tenant_full_stack_rag_application/enrichment_pipelines_provider/entity_extraction/entity_extraction_requirements.txt && 
uv pip install -r ../src/multi_tenant_full_stack_rag_application/bedrock_provider/bedrock_provider_requirements.txt && 
uv pip install -r ../src/multi_tenant_full_stack_rag_application/embeddings_provider/bedrock_embeddings_provider_requirements.txt && 
uv pip install -r ../src/multi_tenant_full_stack_rag_application/utils/utils_requirements.txt && 
# uv pip install -r ../src/multi_tenant_full_stack_rag_application/tools_provider/tools/code_sandbox/requirements_code_sandbox_tool.txt && 
# uv pip install -r ../src/multi_tenant_full_stack_rag_application/tools_provider/tools/code_sandbox/requirements_code_sandbox_host.txt && 
# uv pip install -r ../src/multi_tenant_full_stack_rag_application/tools_provider/tools/web_search_tool/requirements_web_search_tool.txt && 
uv pip install -r ../src/multi_tenant_full_stack_rag_application/ingestion_provider/loaders/pdf_image_loader_requirements.txt && 
# uv pip install -r ../src/multi_tenant_full_stack_rag_application/ingestion_provider/loaders/docx_loader_requirements.txt && 
# uv pip install -r ../src/multi_tenant_full_stack_rag_application/ingestion_provider/vector_ingestion_requirements.txt && 
# uv pip install -r ../src/multi_tenant_full_stack_rag_application/initialization_handler/initialization_handler_requirements.txt && 
# uv pip install -r ../src/multi_tenant_full_stack_rag_application/ingestion_provider/loaders/xlsx_loader_requirements.txt && 
. env.sh  &&
echo STACK_NAME = $STACK_NAME && 
../../.venv/bin/python -m pytest --cov=multi_tenant_full_stack_rag_application -x -s multi_tenant_full_stack_rag_application \
    --ignore=multi_tenant_full_stack_rag_application/tools_provider \
    --ignore=multi_tenant_full_stack_rag_application/ingestion_provider/test_docx_loader.py
    # --ignore=multi_tenant_full_stack_rag_application/generation_handler \
    # --ignore=multi_tenant_full_stack_rag_application/enrichment_pipelines_provider \
    #  --ignore=multi_tenant_full_stack_rag_application/embeddings_provider 
    # --ignore=multi_tenant_full_stack_rag_application/utils 
    # --ignore=multi_tenant_full_stack_rag_application/bedrock_provider \
    # --ignore=multi_tenant_full_stack_rag_application/document_collections_handler \
    # --ignore=multi_tenant_full_stack_rag_application/ingestion_provider \
    # --ignore=multi_tenant_full_stack_rag_application/vector_store_provider \


    
    
