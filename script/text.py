# use aiohttp

import rich
import urllib
import urllib.request
import json

def send_request(url, payload, method="POST"):
    try:
      req = urllib.request.Request(
          url,
          data=json.dumps(payload).encode('utf-8'),
          headers={
              'Content-Type': 'application/json',
              #'Accept': 'application/json',
              #'User-Agent': 'Embedded-Pi-Zero-Client'
          },
          method=method
      )
      with urllib.request.urlopen(req, timeout=3) as response:
          return json.loads(response.read().decode('utf-8'))
    except Exception as exc:
        rich.print(exc)
        #raise

def main():
  BASE_URL="http://localhost:6969"
  res = send_request(f"{BASE_URL}/api/test", None, method="GET")
  #res = send_request(f"{BASE_URL}/api/text", {"text": "Hello world"})
  rich.print(res)

if __name__ == "__main__":
  main()
