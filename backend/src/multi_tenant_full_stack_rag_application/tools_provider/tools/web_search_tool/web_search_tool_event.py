from multi_tenant_full_stack_rag_application.tools_provider.tools.tool_provider_event import ToolProviderEvent

default_x = 5
default_clean_elems = ['javascript', 'scripts', 'style', 'styles']
default_kill_tags = ['img']
default_elem_scrape_order = ['article','body']
valid_operations = ['DOWNLOAD', 'SEARCH', 'SEARCH_AND_DOWNLOAD']


class WebSearchToolEvent(ToolProviderEvent):
    def __init__(self, 
        operation: str='', 
        search_query: str='', 
        top_x: int=default_x,
        clean_elems: [str]=default_clean_elems,
        elem_scrape_order: [str]=default_elem_scrape_order,
        kill_tags: [str]=default_kill_tags,
    ):
        super().__init__(operation)
        self.search_query = search_query
        self.top_x = top_x
        self.clean_elems = clean_elems
        self.elem_scrape_order = elem_scrape_order
        self.kill_tags = kill_tags

    def from_lambda_event(self, evt):
        print(f"web search tool event received evt {evt}")
        self.operation = evt['operation']
        if self.operation not in valid_operations:
            raise Exception(f"ERROR: Received invalid operation {operation}")
        
        if 'args' in evt:
            self.args = evt['args']
            if 'operation' in evt['args']:
                self.tool_operation = evt['args']['operation']
            if 'search_query' in evt['args']:
                self.search_query = evt['args']['search_query']
            if 'top_x' in evt['args']:
                self.top_x = evt['args']['top_x'] 
            else:
                self.top_x = default_x
            if 'clean_elems' in evt['args']:
                self.clean_elems = evt['args']['clean_elems']
            else:
                self.clean_elems = default_clean_elems
            if 'elem_scrape_order' in evt['args']:
                self.elem_scrape_order = evt['args']['elem_scrape_order'] 
            else:
                self.elem_scrape_order = default_elem_scrape_order
            if 'kill_tags' in evt['args']:
                self.kill_tags = evt['args']['kill_tags'] 
            else:
                self.kill_tags = default_kill_tags
        
        return self