import boto3
import sys
import json
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

file_manifest = []

def download_file(old_s3_key):
    global file_manifest
    local_file = f"files/{old_s3_key}"
    print(f"downloading s3://{SOURCE_BUCKET}/{old_s3_key} to {local_file}")
    file_manifest.append(local_file)
    s3.download_file(
        SOURCE_BUCKET,
        old_s3_key,
        local_file
    )

for filename in sys.stdin:
    filename = filename.strip().replace(':', '')
    print("\n\nGOT FILE {}\n\n".format(filename))
    file_manifest.append(f"files/{filename.split('/')[-1]}")
    with open(filename, 'r') as f:
        lines = f.readlines()
    
    found_bucket = False
    i = 0

    while i < len(lines):
        line = lines[i]
        if BUCKET_TO_FIND in line:
            found_bucket = True
        elif found_bucket ==True:
            # the next line after finding the bucket line should land here.
            old_s3_keys = []
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
    
    file_manifest.sort()
    with open('files/file_manifest.txt', 'w') as f_out:
        f_out.write("\n".join(file_manifest) + "\n")

    