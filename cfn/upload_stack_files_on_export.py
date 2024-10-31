import boto3
import sys
import os
import requests

# github_files_base = 'https://raw.githubusercontent.com/aws-samples/multi-tenant-full-stack-rag-application-demo/refs/heads/main/cfn/'

BUCKET_TO_FIND = 'cdk-hnb659fds-assets-${AWS::AccountId}-${AWS::Region}'
REGION = os.getenv('AWS_REGION')
ACCT = os.getenv('AWS_ACCOUNT')
s3 = boto3.client('s3', region_name=REGION)

if not REGION or not ACCT:
    print("AWS_REGION and AWS_ACCOUNT environment variables must be set")
    sys.exit(1)

SOURCE_BUCKET = BUCKET_TO_FIND.replace('${AWS::AccountId}', ACCT).replace('${AWS::Region}', REGION)
print(f"SOURCE_BUCKET: {SOURCE_BUCKET}")
print("Updating files...")

def download_file(old_s3_key):
    local_file = f"./backend/{old_s3_key}"
    print(f"downloading s3://{SOURCE_BUCKET}/{old_s3_key} to {local_file}")
    s3.download_file(
        SOURCE_BUCKET,
        old_s3_key,
        local_file
    )

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

    else:
        # these need to have assets from sub-stacks collected
        # for upload to github.
        i = 0
        while i < len(lines):
            line = lines[i]
            if f"Fn::Sub: {BUCKET_TO_FIND}" in line:
                found_bucket = True
                # line = line.replace(f"Fn::Sub: {BUCKET_TO_REPLACE}", input_values['output_bucket'])
                # output_content += line + "\n"
            elif found_bucket ==True:
                # the next line after finding the bucket line should land here.
                old_s3_keys = []
                old_s3_key = ''
                if 'S3Key: ' in line:
                    old_s3_keys.append(line.split('S3Key: ')[1].strip())
                elif '- /' in line:
                    new_key = line.replace('- /', '').strip()
                    if new_key != '*':
                        old_s3_keys.append(new_key)
                elif 'SourceObjectKeys:' in line:
                    i += 1
                    while lines[i].startswith('- '):
                        old_s3_keys.append(lines[i].replace('- ', '').strip())
                        i += 1
                    # i -= 1
                    
                # now copy the file to the output bucket and target s3 key
                for key in old_s3_keys:
                    print(f"found resource to download: {key} in file {filename}. Downloading...")
                    download_file(key)
                    # set it back until it finds the next one
                found_bucket = False 
            i += 1
    
    

    