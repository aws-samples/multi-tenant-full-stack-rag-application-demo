#!/bin/sh
# export HOME=/asset-input
# touch /asset-input/.bash_profile
apk add npm yarn && \
cd /asset-input && \
if [ -d dist ]; then rm -Rf dist; fi && \
rm -Rf dist && \
if [ -d .cache ]; then rm -Rf .cache; fi && \
rm -Rf .cache && \
echo 'creating aws-exports.js with required backend stack values' && \
echo "HTTP API endpoint is $DOC_COLLECTIONS_API_URL" && \
export ESCAPED_URL=$(echo $DOC_COLLECTIONS_API_URL | sed 's/\//\\\//g') && \
echo $ESCAPED_URL && \
cp aws-exports.js.template aws-exports.js && \
echo "Substituting $APP_NAME for <APP_NAME>" && \
sed -i "s/<APP_NAME>/$APP_NAME/g" aws-exports.js && \
sed -i "s/<APP_NAME>/$APP_NAME/g" index.html && \

# echo "Substituting $ACCOUNT_ID for <ACCOUNT_ID>" && \
# sed -i "s/<ACCOUNT_ID>/$ACCOUNT_ID/g" aws-exports.js && \
echo "Substituting $ESCAPED_URL for <DOC_COLLECTIONS_API_URL> ." && \
sed -i "s/<DOC_COLLECTIONS_API_URL>/$ESCAPED_URL/g" aws-exports.js && \

export ESCAPED_URL=$(echo $ENRICHMENT_PIPELINES_API_URL | sed 's/\//\\\//g') && \
echo $ESCAPED_URL && \
echo "Substituting $ESCAPED_URL for <ENRICHMENT_PIPELINES_API_URL> ." && \
sed -i "s/<ENRICHMENT_PIPELINES_API_URL>/$ESCAPED_URL/g" aws-exports.js && \

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

export ESCAPED_URL=$(echo $SHARING_HANDLER_API_URL | sed 's/\//\\\//g') && \
echo $ESCAPED_URL && \
echo "Substituting $ESCAPED_URL for <SHARING_HANDLER_API_URL> ." && \
sed -i "s/<SHARING_HANDLER_API_URL>/$ESCAPED_URL/g" aws-exports.js && \

export ESCAPED_URL=$(echo $PROMPT_TEMPLATES_API_URL | sed 's/\//\\\//g') && \
echo $ESCAPED_URL && \
echo "Substituting $ESCAPED_URL for <PROMPT_TEMPLATES_API_URL> ." && \
sed -i "s/<PROMPT_TEMPLATES_API_URL>/$ESCAPED_URL/g" aws-exports.js && \
echo "Substituting $AWS_REGION for <REGION>." && \
sed -i "s/<REGION>/$AWS_REGION/g" aws-exports.js && \

echo "Substituting <DOC_COLLECTIONS_BUCKET_NAME> for $DOC_COLLECTIONS_BUCKET_NAME." && \
sed -i "s/<DOC_COLLECTIONS_BUCKET_NAME>/$DOC_COLLECTIONS_BUCKET_NAME/g" aws-exports.js && \
echo "Substituting <IDENTITY_POOL_ID> for $IDENTITY_POOL_ID." && \
sed -i "s/<IDENTITY_POOL_ID>/$IDENTITY_POOL_ID/g" aws-exports.js && \
sed -i "s/<USER_POOL_ID>/$USER_POOL_ID/g" aws-exports.js && \
sed -i "s/<USER_POOL_CLIENT_ID>/$USER_POOL_CLIENT_ID/g" aws-exports.js && \
mv aws-exports.js src/ && \
echo "running yarn to install deps" && \
yarn && \
echo 'Running build' && \
yarn build && \
echo 'build output in dist/?' && \
ls  && \
echo 'Copying dist/* to /asset-output' && \
mv dist/* /asset-output && \
chown -R $BUILD_UID node_modules