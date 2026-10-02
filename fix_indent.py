import sys

with open('app_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_code = '''                    if res_json:
                    if isinstance(res_json, list):'''

new_code = '''                    if isinstance(res_json, list):'''

content = content.replace(old_code, new_code)

with open('app_web.py', 'w', encoding='utf-8') as f:
    f.write(content)
