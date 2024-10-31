import boto3
import sys
import os
import requests

github_files_base = 'https://raw.githubusercontent.com/aws-samples/multi-tenant-full-stack-rag-application-demo/refs/heads/main/cfn/'

input_values = {
    'output_bucket': '',
    'output_prefix': '',
    'ecr_repo_name': '',
    'codebuild_role_arn': ''
}

for val in list(input_values.keys()):
    print(f"Got val from input_values: {val}")
    with open(f'.input_values_cache/{val}', 'r') as f:
        input_values[val] = f.read().strip()

print(f"Input values are: {input_values}")

BUCKET_TO_REPLACE = 'cdk-hnb659fds-assets-${AWS::AccountId}-${AWS::Region}'
REGION = os.getenv('AWS_REGION')
ECR_REPO_TO_REPLACE = 'cdk-hnb659fds-container-assets-${AWS::AccountId}-${AWS::Region}'

ecr = boto3.client('ecr', region_name=REGION)

repo = None
try:
    response = ecr.describe_repositories(
        repositoryNames=[
            input_values['ecr_repo_name'],
        ]
    )
    print(f"Got describe_repos repsonse {response}")
    if "repositories" in response:
        repo = response['repositories'][0]

except Exception as e:
    if "RepositoryNotFoundException" in e.args[0]:
        repo = ecr.create_repository(
            repositoryName=input_values['ecr_repo_name']
        )['repository']
        print(f"created repo {repo}")
 
print(f"Using ECR repo: {repo}")


print("Updating files...")

for filename in sys.stdin:
    filename = filename.strip().replace(':', '')
    print("\n\n{}\n\n".format(filename))
    with open(filename, 'r') as f:
        lines = f.readlines()
    
    output_content = ''
    found_bucket = False

    if filename in [
        "./backend/bedrock-stack-template.yaml",
        "./backend/doc-collections-stack-template.yaml",
    ]:
        # nothing to change in these
        pass

    elif filename in [
        './backend/auth-stack-template.yaml',
        './backend/mtfsrad-stack-template.yaml',
        './backend/vector-store-stack-template.yaml'
    ]:
        for line in lines:
            if f"Fn::Sub: {BUCKET_TO_REPLACE}" in line:
                found_bucket = True
                line = line.replace(f"Fn::Sub: {BUCKET_TO_REPLACE}", input_values['output_bucket'])
                output_content += line + "\n"
            elif found_bucket ==True:
                # the next line after finding the bucket line should land here.
                old_s3_key = line.replace('- /', '').strip()
                s3_key = f"{input_values['output_prefix'] }/{old_s3_key}"
                output_content += f"            - /{s3_key}\n"
                found_bucket = False
                # now copy the file to the output bucket and target s3 key
                print(f"downloading s3://{SOURCE_BUCKET}/{old_s3_key}")
                old_filename = filename.split('/')[-1]
                s3_my_acct.download_file(
                    SOURCE_BUCKET,.
                    old_s3_key,
                    f"/tmp/{old_filename}"
                )
                print(f"uploading s3://{input_values['output_bucket']}/{s3_key}")
                s3_workshop.upload_file(
                    f"/tmp/{old_filename}",
                    input_values['output_bucket'],
                    s3_key
                )
            else:
                output_content += line + "\n"
    elif filename in [
        './cfn/codebuild-stack-template.yaml'
    ]:
        for line in lines:
            if ECR_REPO_TO_REPLACE in line:
                line = f"Location: {repo['repositoryUri']}"
                output_content += line + "\n"
            else:
                output_content += line + "\n"
    
    elif filename in [
        "./backend/ingestion-stack-template.yaml",
        "./backend/prmopt-templates-stack-template.yaml",
    ]:
        for line in lines:
            if BUCKET_TO_REPLACE in line:
                found_bucket = True
                line = line.replace(f"{BUCKET_TO_REPLACE}", input_values['output_bucket'])
                output_content += line + "\n"
            elif found_bucket ==True:
                # the next line after finding the bucket line should land here.
                old_s3_key = line.split(': ')[1]
                s3_key = f"{input_values['output_prefix'] }/{old_s3_key}"
                output_content += f"S3Key: {input_values['output_prefix'] }/{s3_key}\n"
                found_bucket = False
            elif ECR_REPO_TO_REPLACE in line:
                line = line.replace(f"{ECR_REPO_TO_REPLACE}", repo['repositoryUri'])
                output_content += line + "\n"
            else:
                output_content += line + "\n"
    elif filename in [
        "./backend/embeddings-stack-template.yaml",
        "./backend/enrichment-stack-template.yaml",
        "./backend/generation-handler-stack-template.yaml",
        "./backend/graph-store-stack-template.yaml",
    ]:
        if BUCKET_TO_REPLACE in line:
            found_bucket = True
            line = line.replace(f"Fn::Sub: {BUCKET_TO_REPLACE}", input_values['output_bucket'])
            output_content += line + "\n"
        elif found_bucket ==True:
            # the next line after finding the bucket line should land here.
            old_s3_key = line.split(': ')[1]
            s3_key = f"{input_values['output_prefix'] }/{old_s3_key}"
            output_content += f"S3Key: {input_values['output_prefix'] }/{s3_key}\n"
            found_bucket = False
        else:
            output_content += line + "\n"
    print(f"\n\noutput_content is {output_content}\n\n")

    