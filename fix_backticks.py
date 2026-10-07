import sys

with open('app_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

# We need to find the specific corrupted line:
# let nuevoPrecio = document.querySelector(.inline-price[data-id="${id}"]).value;
# and replace it with backticks:
# let nuevoPrecio = document.querySelector(`.inline-price[data-id="${id}"]`).value;

# Let's just do a regex replace to be safe
import re
content = re.sub(r'document\.querySelector\(\.inline-price\[data-id="?\$\{id\}"?\]\)\.value', r'document.querySelector(`.inline-price[data-id="${id}"]`).value', content)

with open('app_web.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("FIXED")
