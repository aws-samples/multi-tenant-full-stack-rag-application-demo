# Optional deployment assets

If you don't have CDK working on your machine, or if you only have access to Windows and my install.sh won't run on your computer, then you can use this optional stack to create a small EC2 instance from which you can deploy this stack.

The t3.medium instance costs less than five cents an hour ($0.0464), but you should still stop the instance when it's not in use, to avoid unnecessary charges after the RAG application stack installs. You can terminate it entirely if you'd like, but if you want to update the stack in the future, it will be easier to stop the instance instead of terminating it, so you can start it back up again later with your local CDK project still retaining the same state.

Use the deployment-instance-cfn.yaml template in the CloudFormation console to create the deployment instance. Then use the Connect feature in the EC2 console, and choose Session Manager. 

Then copy and paste the following commands:

```
sudo su - cdkUser
cd multi-tenant-full-stack-rag-application-demo
```

Then copy and paste your AWS credentials into the terminal session and make sure the following variables are set:

AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_SESSION_TOKEN 

The AWS_SESSION_TOKEN is only needed if your access key is short-term, like from a role, and not long term, like from an IAM user. If your access key starts with AK, you don't need it. If it starts with AS, you'll need the session token as well. If you're using an SSO provider, usually they have a link to copy CLI or programmatic credentials to provide the short-term credentials. You'll need administrative credentials in your account to install this stack.

Test your access by running this command:

```
aws bedrock list-foundation-models
```

If you see a list of models, you'll know you're using a region that supports Bedrock, which is needed for the main stack to install. 

If it complains about not knowing which region to use, then type `aws configure` and pick a default region. You can click enter for the rest of the questions.

Finally, after pasting your credentials and testing your AWS access, you should be able to install the stack by pasting in this command. Note that the -y is optional, and will say "yes" to all sub-stacks that prompt about creating IAM roles. If you don't do this, keep an eye on the install because it will prompt multiple times through the process.

```
'./install.sh -y
```

