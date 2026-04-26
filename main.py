import os
import glob
import webbrowser
import subprocess
import tkinter as tk
from tkinter import filedialog
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from core.set_json import restore_backup
from core import payload, read_directory_path, write_directory_path, process_json


app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

payload_json = {}
library = ""
current_path = read_directory_path()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/generate")
async def handle_request(request: Request):
    global payload_json
    data = await request.json()
    user_text = data.get('text')
    if not user_text:
        raise HTTPException(status_code=400, detail='متن ورودی یافت نشد')
    payload_json = payload(user_text)
    return JSONResponse(content=payload_json)

@app.get("/pip")
async def cmd():
    global library, current_path
    if 'pip' in payload_json:
        library = payload_json['pip']
        try:
            os.chdir(current_path)
            command = f"start cmd /k {library}"
            subprocess.Popen(command, shell=True)
            return JSONResponse(content={'status': 'success', 'message': 'پنجره CMD باز شد و دستور در حال اجراست.'})
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        raise HTTPException(status_code=400, detail='مقدار pip یافت نشد')

@app.get("/path")
async def get_path():
    global current_path
    try:
        return JSONResponse(content={'path': current_path})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/set_json")
async def set_json(request: Request):
    try:
        data = await request.json()
        if not isinstance(data, dict) or "edits" not in data:
            raise HTTPException(status_code=400, detail='داده JSON نامعتبر است.')
        success = process_json(data)
        if success:
            return JSONResponse(content={'status': 'success', 'message': 'تغییرات اعمال شد.'})
        else:
            raise HTTPException(status_code=500, detail='خطا در اعمال تغییرات.')
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/set_path")
async def set_path():
    global current_path
    try:
        root = tk.Tk()
        root.withdraw()  # مخفی کردن پنجره اصلی
        selected_directory = filedialog.askdirectory(title="یک پوشه را انتخاب کنید")
        root.destroy()
        if selected_directory:
            current_path = selected_directory
            write_directory_path(current_path)
            return JSONResponse(content={'status': 'success', 'path': current_path})
        else:
            raise HTTPException(status_code=400, detail='هیچ مسیری انتخاب نشد')
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/list_versions")
async def list_versions():
    backup_dir = os.path.join(read_directory_path(), 'backups')
    versions = []
    if os.path.exists(backup_dir):
        version_dirs = glob.glob(os.path.join(backup_dir, 'version_*'))
        versions = [os.path.basename(version_dir).split('_')[1] for version_dir in version_dirs]
    return JSONResponse(content={'versions': versions})

@app.post("/restore_version/{version}")
async def restore_version(version: str):
    try:
        version_number = int(version)
        if restore_backup(version_number):
            return JSONResponse(content={'status': 'success', 'message': f'Version {version} restored successfully.'})
        else:
            raise HTTPException(status_code=400, detail=f'Failed to restore version {version}.')
    except ValueError:
        raise HTTPException(status_code=400, detail='Invalid version number.')

if __name__ == '__main__':
    import uvicorn
    webbrowser.open("http://127.0.0.1:8000")
    uvicorn.run(app, host='0.0.0.0', port=8000)

