import requests
import json
msg = {}
content = {}
content['userName'] = 'fyf'
content['password'] = 'fyf'
content['mac'] = 'who knows'
msg['content'] = content
response = requests.get('http://127.0.0.1:8893/login', data=json.dumps(msg))
result = response._content
print result



