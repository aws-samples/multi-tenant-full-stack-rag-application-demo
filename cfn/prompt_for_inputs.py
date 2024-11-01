import os


stack_name_prompt_text="Enter a name for your CloudFormation stack ({}):  "
bucket_prompt_text="Enter the name of your S3 bucket to host the CloudFormation templates ({}):  "
prefix_prompt_text="Enter optional S3 path prefix for your CloudFormation templates ({}):  "
ecr_repo_prompt_text="Enter an ECR repository name for the vector ingestion provider Lambda function's docker container. If it doesn't exist, it will be created ({}):  "
codebuild_role_prompt_text="Enter IAM role ARN for CodeBuild to build the vector ingestion provider Lambda function's docker container. If it doesn't exist or you leave it blank, one will be created ({}):  "
allowed_email_domains_prompt_text="Enter the email domains allowed to create accounts, separated by commas: ({}):  "
app_name_prompt_text="Enter the name to be displayed on the application UI ({}):  "
removal_policy_prompt_text="Enter the removal policy for the CloudFormation stack's data resources (like buckets, databases, and opensearch clusters). [RETAIN | DESTROY] ({}):  "
signup_email_body_prompt_text = "Enter the text for the body of the sign-up verification email. Defaults to \"Your verification code is {{####}}\". If you change it, make sure to leave the {{####}} ({}):  "
signup_email_subject_prompt_text = "Enter the subject for the sign-up verification email. Defaults to \"Verification code for {{app_name}}\".  ({}):  "

last_stack_name_input = ''
stack_name = ''
last_app_name_input = ''
app_name = ''
last_removal_policy_input=''
removal_policy = ''
last_signup_email_body_input = ''
signup_email_body = ''
last_signup_email_subject_input = ''
signup_email_subject = ''

last_bucket_input = ''
output_bucket = ''
last_prefix_input = ''
output_prefix = ''
last_ecr_repo_input = ''
ecr_repo = ''
last_codebuild_role_input = ''
codebuild_role = ''
last_allowed_email_domains_input = ''
allowed_email_domains = ''

if not os.path.isdir('.input_values_cache'):
    os.makedirs('.input_values_cache')

def get_variable(prompt_text, value_file, *, default=None, null_ok=False):
    last_variable_val = default
    variable_val = ''
    if os.path.exists(f".input_values_cache/{value_file}"):
        with open(f".input_values_cache/{value_file}", 'r') as f:
            last_variable_val = f.read().strip()
    while variable_val == '':
        text = prompt_text.format(last_variable_val)
        variable_val = input(text)
        if last_variable_val and not variable_val:
            variable_val = last_variable_val
        if null_ok:
            break
    with open(f".input_values_cache/{value_file}", 'w') as f:
        f.write(variable_val)
    return variable_val

stack_name = get_variable(stack_name_prompt_text, 'stack_name')
app_name = get_variable(app_name_prompt_text, 'app_name', default='Multi-tenant, full-stack RAG application demo')
removal_policy = get_variable(removal_policy_prompt_text, 'removal_polcy', default='DESTROY')
allowed_email_domains = get_variable(allowed_email_domains_prompt_text, 'allowed_email_domains')
signup_email_subject = get_variable(signup_email_subject_prompt_text, 'signup_email_subject', default=f'Verification code for {app_name}')
signup_email_body = get_variable(signup_email_body_prompt_text, 'signup_email_body', default=f'Your verification code for {app_name} is {{####}}')
output_bucket = get_variable(bucket_prompt_text, 'output_bucket')
output_prefix = get_variable(prefix_prompt_text, 'output_prefix')
ecr_repo = get_variable(ecr_repo_prompt_text, 'ecr_repo_name')
codebuild_role = get_variable(codebuild_role_prompt_text, 'codebuild_role_arn', null_ok=True)

print(f"Got stack name {stack_name}")
print(f"Got app name {app_name}")
print(f"Got removal policy {removal_policy}")
print(f"Got allowed email domains {allowed_email_domains}")
print(f"Got signup email subject {signup_email_subject}")
print(f"Got signup email body {signup_email_body}")
print(f"Got output bucket {output_bucket}")
print(f"Got output prefix {output_prefix}")
print(f"Got ECR repo {ecr_repo}")
print(f"Got codebuild role {codebuild_role}")
