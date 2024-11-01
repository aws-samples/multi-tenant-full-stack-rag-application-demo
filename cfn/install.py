import boto3
import os

REGION = os.getenv('AWS_REGION')

cfn = boto3.client('cloudformation', region_name=REGION)

response = cfn.create_stack(
    StackName=
)