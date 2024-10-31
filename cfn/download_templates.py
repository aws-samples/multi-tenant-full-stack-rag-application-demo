import requests
from lxml import etree
from lxml.cssselect import CSSSelector

github_files_base = 'https://raw.githubusercontent.com/aws-samples/multi-tenant-full-stack-rag-application-demo/refs/heads/main/cfn/'
github_files_list = 'https://github.com/aws-samples/multi-tenant-full-stack-rag-application-demo/tree/main/cfn/backend'
parser = etree.HTMLParser()

response = requests.get(github_files_list)
print(response.text)
tree = etree.fromstring(response.text, parser)
sel = CSSSelector('a.Link--primary')
for a in sel(tree):
    print(f"[{a.text}]({a.href})")

