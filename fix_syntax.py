import sys

with open('app_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re

# Encontrar la asignacion mala: badgePrecio = <div ... >...</div>;
# Y reemplazarla con backticks
content = re.sub(
    r'badgePrecio = <div([^>]+)>(.+?)</div>;', 
    r'badgePrecio = <div\1>\2</div>;', 
    content
)

with open('app_web.py', 'w', encoding='utf-8') as f:
    f.write(content)
