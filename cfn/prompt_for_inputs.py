import os


bucket_prompt_text="Enter the name of your S3 bucket to host the CloudFormation templates ({}):  "
prefix_prompt_text="Enter optional S3 path prefix for your CloudFormation templates ({}):  "
ecr_repo_prompt_text="Enter an ECR repository name for the vector ingestion provider Lambda function's docker container. If it doesn't exist, it will be created ({}):  "
codebuild_role_prompt_text="Enter IAM role ARN for CodeBuild to build the vector ingestion provider Lambda function's docker container. If it doesn't exist or you leave it blank, one will be created ({}):  "

last_bucket_input = ''
output_bucket = ''
last_prefix_input = ''
output_prefix = ''
last_ecr_repo_input = ''
ecr_repo = ''
last_codebuild_role_input = ''
codebuild_role = ''

if not os.path.isdir('.input_values_cache'):
    os.makedirs('.input_values_cache')

def get_variable(prompt_text, value_file, null_ok=False):
    last_variable_val = None
    variable_val = ''
    if os.path.exists(f".input_values_cache/{value_file}"):
        with open(f".input_values_cache/{value_file}", 'r') as f:
            last_variable_val = f.read().strip()
    while variable_val == '':
        variable_val = input(prompt_text.format(last_variable_val))
        if last_variable_val and not variable_val:
            variable_val = last_variable_val
        if null_ok:
            break
    with open(f".input_values_cache/{value_file}", 'w') as f:
        f.write(variable_val)
    return variable_val

output_bucket = get_variable(bucket_prompt_text, 'output_bucket')
output_prefix = get_variable(prefix_prompt_text, 'output_prefix')
ecr_repo = get_variable(ecr_repo_prompt_text, 'ecr_repo_name')
codebuild_role = get_variable(codebuild_role_prompt_text, 'codebuild_role_arn', null_ok=True)

print(f"Got output bucket {output_bucket}")
print(f"Got output prefix {output_prefix}")
print(f"Got ECR repo {ecr_repo}")
print(f"Got codebuild role {codebuild_role}")
