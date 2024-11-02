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
    'stack_name': '',
    'stack_id': ''
}

print(f"Current directory: {os.getcwd()}")
print(os.listdir(os.getcwd()))

for val in list(input_values.keys()):
    file_path = f'./.input_values_cache/{val}'
    print(f"Does {os.getcwd()}/.input_values_cache/{val} exist?")
    if os.path.exists(file_path):
        print(f"Found {file_path}")
        with open(file_path, 'r') as f:
            value = f.read().strip().strip('/')
            print(f"Got value {value}")
            input_values[val] = value

print(f"Input values are: {input_values}")

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
print(f"Params are {params} ")
template_url = f"https://{input_values['output_bucket']}.s3.{region}.amazonaws.com/{input_values['output_prefix']}/mtfsrad-stack.yaml"
stacks = cfn.list_stacks()['StackSummaries']
print(f"Found existing stacks {stacks}")

stack = None
for existing_stack in stacks:
    stack_name = existing_stack['StackName']
    print(f"Checking if stack name {stack_name} matches {input_values['stack_name']}")
    if stack_name.startswith(input_values['stack_name']) and \
        not existing_stack['StackStatus'].startswith('DELETE'):
        print(f"Found existing stack {stack}")
        stack = existing_stack

print(f"Stack is now {stack}")
if not stack:
    print("Creating stack.")
    stack_response = cfn.create_stack(
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
    print(f"Created stack {stack_response}")
    with open('.input_values_cache/stack_id', 'w') as f_out:
        f_out.write(stack_response['StackId'])

else:
    print("Updating stack.")
    stack = cfn.update_stack(
        StackName=input_values['stack_id'],
        TemplateURL=template_url,
        Parameters=params,
        Capabilities=[
            'CAPABILITY_NAMED_IAM',
            'CAPABILITY_AUTO_EXPAND'
        ]
    )