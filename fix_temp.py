import sys
import re

with open('app_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

import uuid

# Add import uuid at the top if not there
if 'import uuid' not in content:
    content = content.replace('import os', 'import os\nimport uuid')

# Fix temp_sheets_
content = re.sub(r'temp_filename = f"temp_sheets_\{file\.filename\}"', r'temp_filename = f"temp_sheets_{uuid.uuid4().hex}_{file.filename}"', content)
# Fix temp_cols_
content = re.sub(r'temp_filename = f"temp_cols_\{file\.filename\}"', r'temp_filename = f"temp_cols_{uuid.uuid4().hex}_{file.filename}"', content)
# Fix temp_prev_
content = re.sub(r'temp_filename = f"temp_prev_\{file\.filename\}"', r'temp_filename = f"temp_prev_{uuid.uuid4().hex}_{file.filename}"', content)
# Fix temp_
content = re.sub(r'temp_filename = f"temp_\{file\.filename\}"', r'temp_filename = f"temp_{uuid.uuid4().hex}_{file.filename}"', content)

with open('app_web.py', 'w', encoding='utf-8') as f:
    f.write(content)
