import sys
with open('app_web.py', 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace('from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, status', 'from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, status, Body')
with open('app_web.py', 'w', encoding='utf-8') as f:
    f.write(content)
