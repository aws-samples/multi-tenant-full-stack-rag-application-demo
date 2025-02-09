from multi_tenant_full_stack_rag_application.tools_provider.tools.tool_provider_event import ToolProviderEvent
import os


class CodeSandboxOrchestratorEvent(ToolProviderEvent):
    def __init__(self, *, 
        do_architecture: bool,
        do_business_logic: bool,
        do_iac: bool,
        do_tdd: bool,
        next_loop_instructions: str,
        user_id: str,
        user_prompt: str,
        web_search_query: str,
        web_search_top_x: int
    ):
        operation = 'orchestrate_code_sandbox'
        super().__init__(operation)
        self.do_architecture = do_architecture
        self.do_business_logic = do_business_logic
        self.do_iac = do_iac
        self.do_tdd = do_tdd
        self.next_loop_instructions = next_loop_instructions
        self.user_id = user_id
        self.web_search_query = web_search_query
        self.web_search_top_x = web_search_top_x
        
    def from_lambda_event(self, evt):
        pass