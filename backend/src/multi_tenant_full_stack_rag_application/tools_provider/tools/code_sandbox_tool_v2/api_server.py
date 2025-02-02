from typing import Union
from pydantic import BaseModel
from fastapi import FastAPI
import logging

from multi_tenant_full_stack_rag_application.tools_provider.tools.code_sandbox_tool_v2.code_sandbox_host_event import CodeSandboxHostEvent
from multi_tenant_full_stack_rag_application.tools_provider.tools.code_sandbox_tool_v2.code_sandbox_host import CodeSandboxHost
 
logging.basicConfig(filename='/var/log/codesandbox/codesandbox.log', level=logging.INFO)
logger = logging.getLogger(__name__)
app = FastAPI()
csh = None


@app.get("/")
def read_root():
    return "CodeSandboxToolv2 API"

# class SandboxEvent(BaseModel):
#     business_logic_code: str
#     code_image: str
#     code_language: str
#     cpus: int
#     entrypoint_path: str
#     event_id: str
#     iac_code: Union[str, None] = None
#     iac_image: Union[str, None] = None
#     iac_language: Union[str, None] = None
#     install_tdd_reqs: Union[str, None] = None
#     memory_mb: int
#     operation: str
#     tdd_code: Union[str, None] = None
#     tdd_command: Union[str, None] = None
#     tmpdir: str=None


@app.post("/sandbox")
def sandbox(event: CodeSandboxHostEvent):
    logger.info(f"/sandbox received event: {event}")
    global csh
    if not csh:
        csh = CodeSandboxHost()
    # evt = CodeSandboxToolV2Event(**event.__dict__)
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

        