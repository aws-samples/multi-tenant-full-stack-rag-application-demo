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

params = [
    {
        'ParameterKey': 'allowedEmailDomains',
        'ParameterValue': input_values['allowed_email_domains']
    },
    {
        'ParameterKey': 'appName',
        'ParameterValue': input_values['app_name']
    },
    {
        'ParameterKey': 'removalPolicy',
        'ParameterValue': input_values['removal_policy']
    },
    {
        'ParameterKey': 'signUpEmailBody',
        'ParameterValue': input_values['signup_email_body']
    },
    {
        'ParameterKey': 'signUpEmailSubject',
        'ParameterValue': input_values['signup_email_subject']
    } 
]

for val in list(input_values.keys()):
    with open(f'.input_values_cache/{val}', 'r') as f:
        input_values[val] = f.read().strip().strip('/')

print(f"Input values are: {input_values}")

template_url = f"https://{input_values['output_bucket']}.s3.{region}.amazonaws.com/{input_values['output_prefix']}/mtfsrad-stack.yaml"
stacks = cfn.list_stacks()['StackSummaries']
stack = None
for existing_stack in stacks:
    if existing_stack['StackName'].startswith(input_values['stack_name']):
        stack = existing_stack

if not stack:
    stack = cfn.create_stack(
        StackName=input_values['stack_name'],
        TemplateURL=template_url,
        Parameters=params,
        TimeoutInMinutes=60,
        Capabilities=[
            'CAPABILITY_NAMED_IAM',
            'CAPABILITY_AUTO_EXPAND'
        ],
        EnableTerminationProtection=False
    )
else:
    stack = cfn.update_stack(
        StackName=stack['StackName'],
        TemplateURL=template_url,
        Parameters=params,
        Capabilities=[
            'CAPABILITY_NAMED_IAM',
            'CAPABILITY_AUTO_EXPAND'
        ]
    )