#!/usr/bin/env python3
import os

import aws_cdk as cdk

from lib.app import MultiTenantRagStack


app = cdk.App()
MultiTenantRagStack(app, "MultiTenantRagStack")

app.synth()
