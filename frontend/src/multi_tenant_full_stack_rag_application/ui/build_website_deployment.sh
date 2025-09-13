#!/bin/sh
# export HOME=/asset-input
# touch /asset-input/.bash_profile
echo "Starting build_website_deployment.sh" && \
echo "running apt update && install" && \
apt update && apt install node-corepack -y && \
echo "running corepack enable && install" && \
corepack enable && corepack install --all -g && \
cd /asset-input && \
echo "removing previous dist" && \
if [ -d dist ]; then rm -Rf dist; fi && \
echo "removing cache" && \
if [ -d .cache ]; then rm -Rf .cache; fi && \
echo 'creating aws-exports.js with required backend stack values' && \
echo "HTTP API endpoint is $DOC_COLLECTIONS_API_URL" && \
export ESCAPED_URL=$(echo $DOC_COLLECTIONS_API_URL | sed 's/\//\\\//g') && \
echo $ESCAPED_URL && \
cp aws-exports.js.template aws-exports.js && \
echo "Substituting $APP_NAME for <APP_NAME>" && \
sed -i "s/<APP_NAME>/$APP_NAME/g" aws-exports.js && \
sed -i "s/<APP_NAME>/$APP_NAME/g" index.html && \
echo "Substituting $ESCAPED_URL for <DOC_COLLECTIONS_API_URL> ." && \
sed -i "s/<DOC_COLLECTIONS_API_URL>/$ESCAPED_URL/g" aws-exports.js && \
echo "Substituting $ENABLED_ENRICHMENT_PIPELINES for <ENABLED_ENRICHMENT_PIPELINES> ." && \
sed -i "s/<ENABLED_ENRICHMENT_PIPELINES>/$ENABLED_ENRICHMENT_PIPELINES/g" aws-exports.js && \
export ESCAPED_URL=$(echo $GENERATION_API_URL | sed 's/\//\\\//g') && \
echo $ESCAPED_URL && \
echo "Substituting $ESCAPED_URL for <GENERATION_API_URL> ." && \
sed -i "s/<GENERATION_API_URL>/$ESCAPED_URL/g" aws-exports.js && \
echo "Substituting $AWS_REGION for <REGION>." && \
sed -i "s/<REGION>/$AWS_REGION/g" aws-exports.js && \
export ESCAPED_URL=$(echo $INITIALIZATION_API_URL | sed 's/\//\\\//g') && \
echo $ESCAPED_URL && \
echo "Substituting $ESCAPED_URL for <INITIALIZATION_API_URL> ." && \
sed -i "s/<INITIALIZATION_API_URL>/$ESCAPED_URL/g" aws-exports.js && \
export ESCAPED_URL=$(echo $PROMPT_TEMPLATES_API_URL | sed 's/\//\\\//g') && \
echo $ESCAPED_URL && \
echo "Substituting $ESCAPED_URL for <PROMPT_TEMPLATES_API_URL> ." && \
sed -i "s/<PROMPT_TEMPLATES_API_URL>/$ESCAPED_URL/g" aws-exports.js && \
echo "Substituting $AWS_REGION for <REGION>." && \
sed -i "s/<REGION>/$AWS_REGION/g" aws-exports.js && \
echo "Substituting $INGESTION_BUCKET_NAME for <INGESTION_BUCKET_NAME> for ." && \
sed -i "s/<INGESTION_BUCKET_NAME>/$INGESTION_BUCKET_NAME/g" aws-exports.js && \
echo "Substituting <IDENTITY_POOL_ID> for $IDENTITY_POOL_ID." && \
sed -i "s/<IDENTITY_POOL_ID>/$IDENTITY_POOL_ID/g" aws-exports.js && \
sed -i "s/<USER_POOL_ID>/$USER_POOL_ID/g" aws-exports.js && \
sed -i "s/<USER_POOL_CLIENT_ID>/$USER_POOL_CLIENT_ID/g" aws-exports.js && \
mv aws-exports.js src/ && \
echo "aws-exports.js after updates:" && \
cat src/aws-exports.js && \
echo "running yarn to install deps" && \
yarn && \
echo 'Running build' && \
yarn build && \
echo 'build output in dist/?' && \
ls  && \
echo 'Copying dist/* to /asset-output' && \
mv dist/* /asset-output && \
echo "running chown -R $BUILD_UID node_modules" && \
chown -R $BUILD_UID node_modules
