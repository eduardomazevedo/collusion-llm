import os
import config
import sys

print(os.getcwd())

print(sys.path)
print(config.OPENAI_API_KEY)


import wrds
print (wrds.Connection)

conn = wrds.Connection(wrds_username=config.WRDS_USERNAME, password=config.WRDS_PASSWORD)
print(conn)

print(conn.list_libraries())