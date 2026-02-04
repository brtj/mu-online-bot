import requests

def post(url, payload):
    r = requests.post(url, json=payload, timeout=160)
    r.raise_for_status()
    return r.json() if r.content else None

def request_get(url):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json() if r.content else None