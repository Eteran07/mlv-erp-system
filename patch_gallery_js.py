import sys

with open('app_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_js = '''imgs.forEach(item => {
                    cont.innerHTML += \
                        <div class="gallery-item">
                            <img src="\">
                            <span>\</span>
                        </div>
                    \;
                });'''

new_js = '''imgs.forEach(item => {
                    cont.innerHTML += \
                        <div class="gallery-item">
                            <img src="/api/imagen-local/\" loading="lazy">
                            <span>\</span>
                        </div>
                    \;
                });'''

content = content.replace(old_js, new_js)

with open('app_web.py', 'w', encoding='utf-8') as f:
    f.write(content)
