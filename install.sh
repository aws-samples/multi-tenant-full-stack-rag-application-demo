#!/bin/bash
# check if either first or second argument is -y
# -y means "yes" and will skip the confirmation prompts for 
# creating IAM roles (same as --require-approval never)
y=''
# -h means --hotswap-fallback for fast deployment of stack
# changes during development. Don't use in prod. Will introduce
# drift into your stack.
h=''
# pass in -nf to skip frontend install. Only use if 
# doing backend dev work and haven't changed the frontend
f=1
while getopts "yhf" opt; do
  case ${opt} in
    y )
      y=' --require-approval never'
      ;;
    h )
      h=' --hotswap-fallback'
      ;;
    nf )
      f=0
  esac
done

cd backend && 
echo "Installing backend stack. Please wait. It takes a while the first time through." &&
cdk deploy --all --outputs-file ../frontend/backend_outputs.json $y $h && 
cd .. && 
echo "backend installation complete!" && 
# if -f flag is set, install frontend stack
if [ $f ]; then
  cd frontend && 
  echo "Installing frontend stack. Goes faster, but there's a CloudFront distribution, so that takes a good 15 minutes or so the first time." &&
  export BUILD_UID=$UID && 
  echo "BUILD_UID is $BUILD_UID" && 
  cdk deploy --all $y $h && 
  echo "frontend installation complete!"
fi
