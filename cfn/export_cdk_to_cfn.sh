#!/bin/bash
echo "Don't accidentally run this until you save the old cfn templates hand-edited."
exit 0

if [ ! -d ../cfn/files ]
then
  mkdir -p ../cfn/files
fi

rm -Rf ../cfn/files/* && \
cp ../cfn/codebuild-stack-template.yaml ../cfn/files

# rm -Rf ../backend/cdk.out && \
# sudo rm -Rf ../frontend/cdk.out && \
cd ../backend && \

# previously had cdk synth -e --ci --no-staging but removing for troubleshooting.
cdk synth mtfsrad-b-dev | sed '/CDKMetadata/,$d' > ../cfn/files/mtfsrad-final-stack-template.yaml && \
cdk synth mtfsrad-b-dev/AuthProviderStack | sed '/CDKMetadata/,$d' > ../cfn/files/auth-stack-template.yaml && \
cdk synth mtfsrad-b-dev/Vpc | sed '/CDKMetadata/,$d' > ../cfn/files/vpc-stack-template.yaml && \
cdk synth mtfsrad-b-dev/BedrockProviderStack | sed '/CDKMetadata/,$d' > ../cfn/files/bedrock-stack-template.yaml && \
cdk synth mtfsrad-b-dev/EmbeddingsProviderStack | sed '/CDKMetadata/,$d' > ../cfn/files/embeddings-stack-template.yaml && \
cdk synth mtfsrad-b-dev/IngestionProviderStack | sed '/CDKMetadata/,$d' > ../cfn/files/ingestion-stack-template.yaml && \
cdk synth mtfsrad-b-dev/VectorStoreProviderStack | sed '/CDKMetadata/,$d' > ../cfn/files/vector-store-stack-template.yaml && \
cdk synth mtfsrad-b-dev/DocumentCollectionsHandlerStack | sed '/CDKMetadata/,$d' > ../cfn/files/doc-collections-stack-template.yaml && \
cdk synth mtfsrad-b-dev/PromptTemplateHandlerStack | sed '/CDKMetadata/,$d' > ../cfn/files/prompt-templates-stack-template.yaml && \
cdk synth mtfsrad-b-dev/GraphStoreProviderStack | sed '/CDKMetadata/,$d' > ../cfn/files/graph-store-stack-template.yaml && \
cdk synth mtfsrad-b-dev/EnrichmentPipelinesHandlerStack | sed '/CDKMetadata/,$d' > ../cfn/files/enrichment-pipelines-stack-template.yaml && \
cdk synth mtfsrad-b-dev/GenerationHandlerApiStack | sed '/CDKMetadata/,$d' > ../cfn/files/generation-handler-stack-template.yaml && \

cd ../frontend && \
export BUILD_UID=$UID && \
cdk synth mtfsrad-f-dev | sed '/CDKMetadata/,$d' > ../cfn/files/ui-stack-template.yaml && \
cd ../cfn && \
# create zip file for Codebuild docker build requirements for ingestion and UI
rm files/ingestion_provider.zip && \
zip -r ingestion_provider.zip ../backend/src/multi_tenant_full_stack_rag_application/ingestion_provider/loaders/*.py && \
zip -r ingestion_provider.zip ../backend/src/multi_tenant_full_stack_rag_application/ingestion_provider/loaders/*.txt && \
zip -r ingestion_provider.zip ../backend/src/multi_tenant_full_stack_rag_application/ingestion_provider/splitters/*.py && \
zip ingestion_provider.zip ../backend/src/multi_tenant_full_stack_rag_application/ingestion_provider/vector_ingestion*.py && \
zip ingestion_provider.zip ../backend/src/multi_tenant_full_stack_rag_application/ingestion_provider/ingestion_status.py && \
zip ingestion_provider.zip ../backend/src/multi_tenant_full_stack_rag_application/ingestion_provider/*.txt && \
zip ingestion_provider.zip ../backend/src/multi_tenant_full_stack_rag_application/ingestion_provider/Dockerfile.vector_ingestion_provider && \
mv ingestion_provider.zip files/ && \
rm files/ui.zip && \
zip -r ui.zip ../frontend/src/multi_tenant_full_stack_rag_application/ui/src && \
zip ui.zip ../frontend/src/multi_tenant_full_stack_rag_application/ui/aws-exports.js.template && \
zip ui.zip ../frontend/src/multi_tenant_full_stack_rag_application/ui/build_website_deployment.sh && \
zip ui.zip ../frontend/src/multi_tenant_full_stack_rag_application/ui/index.html && \
zip ui.zip ../frontend/src/multi_tenant_full_stack_rag_application/ui/*.json && \
zip ui.zip ../frontend/src/multi_tenant_full_stack_rag_application/ui/vite.config.js && \
zip ui.zip ../frontend/src/multi_tenant_full_stack_rag_application/ui/yarn.lock && \
zip ui.zip ../frontend/app.py && \
zip ui.zip ../frontend/requirements.txt && \
mv ui.zip files/ && \
cp mtfsrad-stack.yaml files/ && \
find ./files -name '*.yaml' | python upload_stack_files_on_export.py && \
git add ../cfn && \
git commit -m 'cloudformation export' && \
git push && \
echo "Export complete."
