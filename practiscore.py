#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3 python3Packages.requests python3Packages.beautifulsoup4

print('Hello!')

import requests
from bs4 import BeautifulSoup

url = 'https://practiscore.com/results/new/287616'

# Define headers to mimic a browser
headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Cache-Control': 'max-age=0'
}

# Make the request with headers
response = requests.get(url, headers=headers)

# Uncomment this line if you want to use Beautiful Soup to parse the response
# soup = BeautifulSoup(response.text, 'html.parser')

print(response.text)

open('output.html', 'w').write(response.text)