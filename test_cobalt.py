import requests
import json

try:
    r = requests.get('https://instances.hyper.lol/instances.json', timeout=10)
    data = r.json()
    instances = [i['api'] for i in data if i.get('api') and i.get('version') and (i['version'].startswith('10.') or i['version'].startswith('9.') or i['version'].startswith('8.'))]
    print(f'Found {len(instances)} Cobalt instances.')
    
    for url in instances:
        print(f'Trying {url}...')
        try:
            res = requests.post(
                url,
                headers={'Accept':'application/json'},
                json={'url':'https://www.youtube.com/watch?v=dQw4w9WgXcQ', 'isAudioOnly':True},
                timeout=5
            )
            if res.status_code == 200:
                print('SUCCESS:', url)
                print(res.json())
                break
            else:
                print('FAIL STATUS:', res.status_code)
        except Exception as e:
            print('FAIL ERROR:', str(e))
except Exception as e:
    print('Failed to fetch instances:', str(e))
