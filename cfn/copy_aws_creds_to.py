import os
import sys

prefix = sys.argv[1]
print(f"Adding {prefix} to AWS variables")
print(f"export {prefix}_AWS_ACCESS_KEY_ID={os.getenv('AWS_ACCESS_KEY_ID')}")
print(f"export {prefix}_AWS_SECRET_ACCESS_KEY={os.getenv('AWS_SECRET_ACCESS_KEY')}")
print(f"export {prefix}_AWS_SESSION_TOKEN={os.getenv('AWS_SESSION_TOKEN')}")
