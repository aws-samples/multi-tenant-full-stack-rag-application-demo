#!/bin/bash
echo Started install at `date`
export SECONDS=0
# check if either first or second argument is -y
# -y means "yes" and will skip the confirmation prompts for 
# creating IAM roles (same as --require-approval never)
y=''
# -h means --hotswap-fallback for fast deployment of stack
# changes during development. Don't use in prod. Will introduce
# drift into your stack.
h=''
# pass in -f to skip frontend install. Only use if 
# doing backend dev work and haven't changed the frontend
f=1
# pass in -b to skip backend install. Only use if doing frontend
# dev work and haven't changed the backend.
b=1

while getopts "yhfb" opt; do
  case ${opt} in
    y )
      y=' --require-approval never'
      ;;
    h )
      h=' --hotswap-fallback'
      ;;
    f )
      f=0
      ;;
    b )
      b=0
      ;;
  esac
done

if [ ! -f .venv/bin/activate ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip3 install --upgrade --no-cache -r backend/requirements.txt
pip3 install --upgrade --no-cache -r frontend/requirements.txt

aws iam create-service-linked-role --aws-service-name opensearchservice.amazonaws.com

if [ $b -eq 1 ]; then
  cd backend
  echo
  echo
  echo "Installing backend stack. Please wait. It takes a while the first time through."
  echo
  cdk deploy --all --asset-parallelism true --concurrency 50 --outputs-file ../frontend/backend_outputs.json $y $h 
  if [ $? -ne 0 ]; then
    echo "cdk deploy failed. Exiting."
    exit
  fi
  cd ..
  echo
  echo "backend installation complete!" 
  echo
fi
# if -f flag is set, install frontend stack
echo "Do frontend? ${f}"
if [ $f -eq 1 ]; then
  cd frontend
  echo "Installing frontend stack. Goes faster, but there's a CloudFront distribution, so that takes a good 15 minutes or so the first time."
  export BUILD_UID=$UID 
  echo "BUILD_UID is $BUILD_UID" 
  cdk deploy --all --asset-parallelism true --concurrency 50 $y $h 
  if [ $? -ne 0 ]; then
    echo "cdk deploy failed. Exiting."
    exit
  fi
  echo
  echo "frontend installation complete!"
fi
echo
echo Installation complete!
echo elapsed time: $(($SECONDS / 60)) minutes and $(($SECONDS % 60)) seconds
echo
