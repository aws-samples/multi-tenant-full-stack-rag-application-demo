#!/bin/bash

rm -Rf cfn/backend
rm -Rf cfn/frontend
rm -Rf backend/cdk.out
rm -Rf frontend/cdk.out
mkdir cfn/backend
mkdir cfn/frontend
cd backend && cdk synth && \
export BUILD_UID=$UID && \
cd ../frontend && cdk synth && \
cd ../cfn && \
cp -aR ../backend/cdk.out/* backend/ && \
cp -aR ../frontend/cdk.out/* frontend/ && \
cd ../ && \
git add cfn/* && \
git commit -m "Cloudformation packaging" && \
git push origin main && \
echo "Cloudformation packaging complete."