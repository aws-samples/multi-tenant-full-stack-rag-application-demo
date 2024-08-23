#!/usr/bin/env python3
import os

import aws_cdk as cdk

from lib.app import MultiTenantRagStack


app = cdk.App()
MultiTenantRagStack(app, app.node.try_get_context('stack_name_backend') or "MultiTenantRagStack")

app.synth()
