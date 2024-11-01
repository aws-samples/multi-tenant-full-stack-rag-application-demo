import boto3
import os


region = os.getenv('AWS_REGION')
cfn = boto3.client('cloudformation', region_name=region)

input_values = {
    'allowed_email_domains': '',
    'app_name': '',
    'codebuild_role_arn': '',
    'ecr_repo_name': '',
    'output_bucket': '',
    'output_prefix': '',
    'removal_policy': '',
    'signup_email_body': '',
    'signup_email_subject': '',
    'stack_name': ''
}

for val in list(input_values.keys()):
    with open(f'.input_values_cache/{val}', 'r') as f:
        input_values[val] = f.read().strip().strip('/')

print(f"Input values are: {input_values}")

stack = cfn.create_stack(
    StackName=input_values['stack_name'],
    TemplateURL=f"https://{input_values['output_bucket']}.s3.{region}.amazonaws.com/{input_values['output_prefix']}/mtfsrad-stack.yaml",
    Parameters=[
        {
            'ParameterKey': 'AllowedEmailDomains',
            'ParameterValue': input_values['allowed_email_domains']
        },
        {
            'ParameterKey': 'AppName',
            'ParameterValue': input_values['app_name']
        },
        {
            'ParameterKey': 'CodeBuildRoleArn',
            'ParameterValue': input_values['codebuild_role_arn']
        },
        {
            'ParameterKey': 'ECRRepoName',
            'ParameterValue': input_values['ecr_repo_name']
        },
        {
            'ParameterKey': 'OutputBucket',
            'ParameterValue': input_values['output_bucket']
        },
        {
            'ParameterKey': 'OutputPrefix',
            'ParameterValue': input_values['output_prefix']
        },
        {
            'ParameterKey': 'RemovalPolicy',
            'ParameterValue': input_values['removal_policy']
        },
        {
            'ParameterKey': 'SignupEmailBody',
            'ParameterValue': input_values['signup_email_body']
        },
        {
            'ParameterKey': 'SignupEmailSubject',
            'ParameterValue': input_values['signup_email_subject']
        }
    ],
    TimoutInMinutes=60,
    Capabilities=[
        'CAPABILITY_NAMED_IAM',
        'CAPABILITY_AUTO_EXPAND'
    ],
    EnableTerminationProtection=False
)