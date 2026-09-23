"""Supply an encrypted provider key over an authenticated local connection, never argv."""
import getpass
import json
import urllib.request
import urllib.error

base = 'http://127.0.0.1:8080/api/v1'
token = getpass.getpass('Administrator access token (hidden): ')
slot = input('Model slot [primary/fallback/offline]: ').strip()
if slot not in {'primary', 'fallback', 'offline'}:
    raise SystemExit('Invalid slot')
headers = {'Authorization': 'Bearer '+token, 'Content-Type':'application/json'}
try:
    with urllib.request.urlopen(urllib.request.Request(base+'/copilot/models', headers=headers), timeout=10) as response:
        config = json.load(response)[slot]
    config.pop('has_key', None)
    config['api_key'] = getpass.getpass('Provider key (hidden; blank clears stored key): ')
    request = urllib.request.Request(base+'/copilot/models/'+slot, data=json.dumps(config).encode(), headers=headers, method='PUT')
    with urllib.request.urlopen(request, timeout=10):
        print('Encrypted provider key updated.')
except urllib.error.HTTPError as error:
    raise SystemExit('Configuration rejected: HTTP '+str(error.code)) from None
finally:
    token = ''
