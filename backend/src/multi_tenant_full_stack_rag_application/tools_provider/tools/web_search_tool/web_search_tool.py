# import requests
from googlesearch import search
import lxml
import lxml.html as html
import requests
import sys
from lxml.html.clean import Cleaner

from multi_tenant_full_stack_rag_application.tools_provider.tools.tool_provider import ToolProvider
from .web_search_tool_event import WebSearchToolEvent

# gst = None
# cleaner = None
# print(f"LXML VERSION: {lxml.__version__}")


class WebSearchTool(ToolProvider):
    def __init__(self):
         super().__init__()
         self.cleaner = Cleaner()

    def download(self, url, clean_elems, kill_tags):
        if 'javascript' in clean_elems:
            self.cleaner.javascript = True
        if 'scripts' in clean_elems:
            self.cleaner.scripts = True
        if 'style' in clean_elems:
            self.cleaner.style = True
        if 'styles' in clean_elems:
            self.cleaner.styles = True
        self.cleaner.kill_tags = kill_tags
        print(f"Getting url {url}")
        response = requests.get(url)

        text = None
        if isinstance(response.text, bytes):
            text = response.text.decode('utf-8')
        else:
            text = response.text
        tree = html.fromstring(text)
        title = str(tree.xpath("//title/text()")[0])
        result = self.cleaner.clean_html(html.document_fromstring(text)).text_content()
        if isinstance(result, bytes):
            result = result.decode('utf-8') # .replace('\n','').replace('\t', '')
        elif not isinstance(result, str):
            # might be a StringElement
            result = str(result)

        return {
            "url": url,
            "title": title,
            "text": result.replace('\n', "\n").replace('\t', "\t")
        }

    @staticmethod
    def get_inputs():
        return {
            "operation": {
                "required": True,
                "type": "string",
                "description": "The operation to execute on the tool. Options are [DOWNLOAD | SEARCH | SEARCH_AND_DOWNLOAD]",
                "default": "SEARCH_AND_DOWNLOAD"
            },
            "search_query": {
                "required": True,
                "type": "string",
                "description": "The query string for the search."
            },
            "top_x": {
                "required": False,
                "type": "int",
                "description": "the number of search results to return.",
                "default": 5
            },
            "clean_elems": {
                "required": False,
                "type": "[str]",
                "description": "list of elements to use with lxml.html.clean.Cleaner",
                "default": ['javascript', 'scripts', 'style', 'styles']
            },
            "default_elem_scrape_order": {
                "required": False,
                "type": "[str]",
                "description": "list of elements in order of preference to extract from the page. Stops at first one it finds.",
                "default": ['article', 'body']
            }
        }

    @staticmethod
    def get_outputs():
        return {
            "results": {
                "url of result": {
                   "title": "title of the web page",
                   "text": "cleaned html from result page"
                }
            }
        }

    def handler(self, evt):
        handler_evt = WebSearchToolEvent().from_lambda_event(evt)
        print(f"WebSearchToolEvent is now {handler_evt.__dict__}")
        result = self.run_tool(
            handler_evt.tool_operation,
            handler_evt.search_query,
            handler_evt.top_x,
            handler_evt.clean_elems,
            handler_evt.elem_scrape_order,
            handler_evt.kill_tags,
        )
        print(f"Result from web search tool: {result}")
        return result

    def run_tool(self, 
        operation,
        search_query, 
        top_x, 
        clean_elems,
        elem_scrape_order, 
        kill_tags
    ):
        print(f"run_tool got search_query {search_query}, top_x {top_x} ")
        if operation == 'DOWNLOAD':
            # for download operations the search query value should be the URL.
            results = self.download(search_query, clean_elems, kill_tags)

        elif operation == 'SEARCH': 
            results = self.search(search_query, top_x)

        elif operation == 'SEARCH_AND_DOWNLOAD':
            result_items = self.search(search_query, top_x)
            print(f"Got search results {result_items}")
            results = {}
            for item in result_items:
                # print(dir(item))
                # print(item.__dict__)
                url = item['url']
                result = self.download(url, clean_elems, kill_tags)
                results[url] = result

        print(f"Got results {results}")
        return {
            "statusCode": '200',
            "body": results
        }

    def search(self, search_query, top_x):
        print(f"Searching f")
        response = search(search_query, num_results=top_x, advanced=True)
        # print(f"Response from search: {response.__dict__}")
        print(dir(response))
        result_items = []
        for item in response:
            print(f"Got item of type {type(item)}, value {item.__dict__}")
            # url = item.url
            result_items.append(item.__dict__)
        return result_items

    def search_and_download(self, 
        search_query, 
        top_x, 
        clean_elems,
        elem_scrape_order, 
        kill_tags
    ):
        search_results = self.search(search_query, top_x)
        results = {}
        for item in search_results:
            result = self.download(item['url'], clean_elems, kill_tags)
            print(f"result: {result}, type: {type(result)}")
            results[item['url']] = result
        return results
