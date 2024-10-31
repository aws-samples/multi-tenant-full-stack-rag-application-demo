#!/bin/bash

rm -Rf ../cfn/backend/* && \
rm -Rf ../cfn/frontend/* && \
rm -Rf ../backend/cdk.out && \
sudo rm -Rf ../frontend/cdk.out && \
cd ../backend && \

# previously had cdk synth -e --ci --no-staging but removing for troubleshooting.
cdk synth mtfsrad-b-dev | sed '/CDKMetadata/,$d' > ../cfn/backend/mtfsrad-stack-template.yaml && \
cdk synth mtfsrad-b-dev/AuthProviderStack | sed '/CDKMetadata/,$d' > ../cfn/backend/auth-stack-template.yaml && \
cdk synth mtfsrad-b-dev/Vpc | sed '/CDKMetadata/,$d' > ../cfn/backend/vpc-stack-template.yaml && \
cdk synth mtfsrad-b-dev/BedrockProviderStack | sed '/CDKMetadata/,$d' > ../cfn/backend/bedrock-stack-template.yaml && \
cdk synth mtfsrad-b-dev/EmbeddingsProviderStack | sed '/CDKMetadata/,$d' > ../cfn/backend/embeddings-stack-template.yaml && \
cdk synth mtfsrad-b-dev/IngestionProviderStack | sed '/CDKMetadata/,$d' > ../cfn/backend/ingestion-stack-template.yaml && \
cdk synth mtfsrad-b-dev/VectorStoreProviderStack | sed '/CDKMetadata/,$d' > ../cfn/backend/vector-store-stack-template.yaml && \
cdk synth mtfsrad-b-dev/DocumentCollectionsHandlerStack | sed '/CDKMetadata/,$d' > ../cfn/backend/doc-collections-stack-template.yaml && \
cdk synth mtfsrad-b-dev/PromptTemplateHandlerStack | sed '/CDKMetadata/,$d' > ../cfn/backend/prompt-templates-stack-template.yaml && \
cdk synth mtfsrad-b-dev/GraphStoreProviderStack | sed '/CDKMetadata/,$d' > ../cfn/backend/graph-store-stack-template.yaml && \
cdk synth mtfsrad-b-dev/EnrichmentPipelinesHandlerStack | sed '/CDKMetadata/,$d' > ../cfn/backend/enrichment-pipelines-stack-template.yaml && \
cdk synth mtfsrad-b-dev/GenerationHandlerApiStack | sed '/CDKMetadata/,$d' > ../cfn/backend/generation-handler-stack-template.yaml && \

cd ../frontend && \
export BUILD_UID=$UID && \
cdk synth mtfsrad-f-dev | sed '/CDKMetadata/,$d' > ../cfn/frontend/ui-stack-template.yaml && \
export OUTPUT_BUCKET=ws-assets-us-east-1 && \
export S3_PREFIX=e03d64e5-c828-4f3b-8143-98a7e3dd7978 && \
cd ../cfn && \
find ./ -name '*.yaml' | xargs grep cdk-hnb659fds-assets | cut -d ' ' -f 1 | uniq | python upload_stack_files_on_export.py && \
git add ../cfn && \
git commit -m 'cloudformation export' && \
git push origin main && \
echo "Export complete."
