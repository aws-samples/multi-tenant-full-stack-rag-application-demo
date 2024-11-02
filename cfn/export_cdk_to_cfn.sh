#!/bin/bash

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
cp mtfsrad-stack.yaml files/ && \
find ./files -name '*.yaml' | python upload_stack_files_on_export.py && \
git add ../cfn && \
git commit -m 'cloudformation export' && \
git push && \
echo "Export complete."
