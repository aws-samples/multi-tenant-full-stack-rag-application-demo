#!/bin/bash
echo Started install at `date`
export SECONDS=0
export SECONDS=0

DOWNLOAD=false
RUN=false

MODE=$1
if [ -z "$MODE" ]; then
  MODE="-d"
fi
# download is default

show_help() {
  echo
  echo 'Usage instructions:'
  echo ' -d | --download : download but do not install'
  echo ' -r | --run : download if not already downloaded, and run'
  echo
  echo "Don't use both at once. You can use download only to inspect the CloudFormation templates before installing. They'll be downloaded to the cfn_templates directory, created where you ran the installer. To do both at once do -r and it will download files if they don't exist locally."
  echo
}

while true
do
    case $MODE in 
        -h | --help ) show_help; exit 0;;
        -d | --download ) DOWNLOAD=true; break;;
        -r | --run ) RUN=true; break;;
        * ) break ;;
    esac
done

echo "Running in mode $MODE"


if [ "$DOWNLOAD" = true ]; then
  echo "Downloading CloudFormation templates"
  if [ -d cfn_templates ]; then
    rm -Rf cfn_templates
  fi
  mkdir -p cfn_templates
  github_files_base='https://raw.githubusercontent.com/aws-samples/multi-tenant-full-stack-rag-application-demo/refs/heads/main/cfn'
  echo downloading $github_files_base/files/file_manifest.txt
  curl $github_files_base/files/file_manifest.txt -o ./cfn_templates/file_manifest.txt
  while IFS= read -r line; do
    echo "Downloading $line"
    local_file=${line:6}
    curl $github_files_base/$line -o cfn_templates/$local_file
  done < cfn_templates/file_manifest.txt
  echo "Downloading install.py"
  curl $github_files_base/install.py -o install.py
  curl $github_files_base/prompt_for_inputs.py -o prompt_for_inputs.py
  curl $github_files_base/update_files_on_install.py -o update_files_on_install.py
  curl $github_files_base/installer_requirements.txt -o installer_requirements.txt
  if [ ! -d .venv ]
    then 
      python3 -m venv .venv
      . .venv/bin/activate
      pip install -r installer_requirements.txt
    else
      . .venv/bin/activate
  fi
  print("Prompting for inputs")
  python3 prompt_for_inputs.py
  find ./cfn_templates | python update_files_on_install.py
fi

if [ "$RUN" = true ]; then
  echo "Installing CloudFormation stacks..."
  python3 install.py
fi