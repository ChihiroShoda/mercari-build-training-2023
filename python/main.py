import os
import logging
import pathlib
import json
import hashlib
import shutil
from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
logger = logging.getLogger("uvicorn")
logger.level = logging.INFO
images = pathlib.Path(__file__).parent.resolve() / "images"
origins = [ os.environ.get('FRONT_URL', 'http://localhost:3000') ]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET","POST","PUT","DELETE"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Hello, world!"}

@app.post("/items")
def add_item(name: str = Form(...), category: str = Form(...), image: UploadFile = Form(...)):
    # imageのhash化
    file_name = image.filename
    hash_file_name = hashlib.sha256(file_name.encode('utf-8')).hexdigest() + ".jpg"
    upload_dir = open(os.path.join("images/", hash_file_name),'wb+')
    shutil.copyfileobj(image.file, upload_dir)

    # jsonファイルの読み込み / 書き込み
    with open('items.json') as f:
        items = json.load(f)
    items["items"].append({"name": name, "category": category, "image_filename": hash_file_name})
    with open('items.json', 'wt') as f:
        json.dump(items, f)

    logger.info(f"Receive item: {name} (category: {category}, image: {file_name})")
    return {"message": f"item received: {name}"}

@app.get("/items")
def get_item():
    with open('items.json') as f:
        items = json.load(f)
    return items

@app.get("/image/{image_filename}")
async def get_image(image_filename):
    # Create image path
    image = images / image_filename

    if not image_filename.endswith(".jpg"):
        raise HTTPException(status_code=400, detail="Image path does not end with .jpg")

    if not image.exists():
        logger.debug(f"Image not found: {image}")
        image = images / "default.jpg"

    return FileResponse(image)