import boto3
import json
import os
import sys
import yaml

if not os.path.isdir('.input_values_cache'):
    os.mkdirs('.input_values_cache')

input_values = {}
input_values_files = os.listdir('.input_values_cache')

for val in input_values_files:
    filepath = f'.input_values_cache/{val}'
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            input_values[val] = f.read().strip().strip('/')

print(f"Input values are: {input_values}")

BUCKET_TO_REPLACE = 'cdk-hnb659fds-assets-${AWS::AccountId}-${AWS::Region}'
REGION = os.getenv('AWS_REGION')
ECR_REPO_TO_REPLACE = 'cdk-hnb659fds-container-assets-${AWS::AccountId}-${AWS::Region}'

s3 = boto3.client('s3', region_name=REGION)
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
files_to_process = []


def process_yaml_file(filename):
    with open(filename, 'r') as f:
        lines = f.readlines()
        output_content = ''
        found_bucket = False
        i = 0
        while i < len(lines):
            line = lines[i].strip("\n")

            if 'mtfsrad-b-dev' in line:
                line = line.replace('mtfsrad-b-dev', input_values['stack_name'])
            if 'mtfsradbdev' in line:
                line = line.replace('mtfsradbdev', input_values['stack_name'].replace('-', ''))
            
            if 'mtfsrad-f-dev' in line: 
                line = line.replace('mtfsrad-f-dev', input_values['stack_name'])
            if 'mtfsradfdev' in line:
                line = line.replace('mtfsradfdev', input_values['stack_name'].replace('-', ''))

            if '{region}' in line:
                line = line.replace('{region}', REGION)
            
            if '{output_prefix}' in line:
                line = line.replace('{output_prefix}', input_values['output_prefix'])
                
            if ECR_REPO_TO_REPLACE in line:
                line = line.replace(ECR_REPO_TO_REPLACE, repo['repositoryUri'])
                output_content += line + "\n"
                found_bucket = False

            elif 'ALLOWED_EMAIL_DOMAINS: ' in line:
                line = line.replace('amazon.com', input_values['allowed_email_domains'])
                output_content += line + "\n"
                
            elif BUCKET_TO_REPLACE in line:
                found_bucket = True
                if f"Fn::Sub: {BUCKET_TO_REPLACE}" in line:
                    line = line.replace(f"Fn::Sub: {BUCKET_TO_REPLACE}", input_values['output_bucket'])
                    output_content += line + "\n"
                else:
                    line = line.replace(BUCKET_TO_REPLACE, input_values['output_bucket'])
                    output_content += line + "\n"

            elif found_bucket ==True:
                # the next line after finding the bucket line should land here.
                if 'S3Key: ' in line:
                    old_s3_key = line.split(': ')[1].strip()
                    s3_key = f"{input_values['output_prefix'] }/{old_s3_key}".replace('.json','.yaml')
                    output_content += line.replace(old_s3_key, s3_key) + "\n"
                elif '- /' in line:
                    old_key = line.replace('- /', '').strip()
                    if old_key != '*':
                        new_key = f"/{input_values['output_prefix'] }/{old_key}".replace('.json','.yaml')
                        output_content += f"            - {new_key}\n"
                    else:
                        output_content += line
                elif 'SourceObjectKeys' in line:
                    output_content += line + "\n"
                    i += 1
                    while lines[i].strip().startswith('- '):
                        old_key = lines[i].replace('- ', '').strip()
                        new_key = f"/{input_values['output_prefix'] }/{old_key}".replace('.json','.yaml')
                        output_content += f"            - {new_key}\n"
                        i += 1
                    i -= 1
                found_bucket = False
                # now copy the file to the output bucket and target s3 key
            else:
                found_bucket = False
                output_content += line + "\n"
            i += 1

        # print(f"\n\noutput_content is {output_content}\n\n")
        with open(filename, 'w') as f:
            f.write(output_content)
    
for filename in sys.stdin:
    filename = filename.strip().replace(':', '')
    if filename == './cfn_templates':
            continue
    files_to_process.append(filename)

    # elif filename.endswith('.json'):
    #     with open(filename, 'r') as f:
    #         content = f.read()
    #     template_js = json.loads(content)
    #     template_yaml = yaml.dump(template_js)
    #     filename = filename.replace('.json', '.yaml')
    #     with open(filename, 'w') as f:
    #         f.write(template_yaml)
    #     process_yaml_file(filename)
    
for filename in files_to_process:
    if filename.endswith('.yaml'):
        process_yaml_file(filename)
    elif filename.endswith('.json'):
        with open(filename, 'r') as f:
            data = f.read()
            print(f"filename {filename} had data {data}")
            data = json.loads(f.read())
            data = yaml.dump(data)
        filename = filename.replace('.json', '.yaml')
        with open(filename, 'w') as f:
            f.write(data)
        process_yaml_file(filename)
    s3_key = f"{input_values['output_prefix']}/{filename.split('/')[-1]}"
    print(f"uploading s3://{input_values['output_bucket']}/{s3_key}")
    s3.upload_file(
        filename,
        input_values['output_bucket'],
        s3_key
    )

    