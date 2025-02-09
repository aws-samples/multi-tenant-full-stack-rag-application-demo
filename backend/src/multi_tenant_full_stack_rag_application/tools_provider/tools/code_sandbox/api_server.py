from typing import Union
from pydantic import BaseModel
from fastapi import FastAPI
import logging

from multi_tenant_full_stack_rag_application.tools_provider.tools.code_sandbox.code_sandbox_host_event import CodeSandboxHostEvent
from multi_tenant_full_stack_rag_application.tools_provider.tools.code_sandbox.code_sandbox_host import CodeSandboxHost
 
logging.basicConfig(filename='/var/log/codesandbox/codesandbox.log', level=logging.INFO)
logger = logging.getLogger(__name__)
app = FastAPI()
csh = None


@app.get("/")
def read_root():
    return "CodeSandboxToolv2 API"


@app.post("/sandbox")
def sandbox(event: CodeSandboxHostEvent):
    logger.info(f"/sandbox received event: {event}")
    global csh
    if not csh:
        csh = CodeSandboxHost()
    # evt = CodeSandboxRunnerEvent(**event.__dict__)
    response = csh.build_image(event)
    logger.info(f"build_image got response {response}")
    if response['exit_code'] != 0:
        return {"error": response}

    else:
        run_response = csh.run_tool(
            response['image_id'],
        )
        return {"response": {
            "build_response": response,
            "run_response": run_response
        }}

        