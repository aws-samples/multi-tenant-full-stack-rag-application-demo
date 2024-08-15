 #!/bin/bash
cd /home/ec2-user
python3 -m pip install -U pip
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
export NVM_DIR=$HOME/.nvm
[ -s '$NVM_DIR/nvm.sh' ] && \. '$NVM_DIR/nvm.sh' 
[ -s '$NVM_DIR/bash_completion' ] && \. '$NVM_DIR/bash_completion'  
nvm install 20
npm install -g aws-cdk
git clone https://github.com/aws-samples/multi-tenant-full-stack-rag-application-demo.git
    