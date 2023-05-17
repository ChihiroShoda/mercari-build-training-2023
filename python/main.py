import os
import logging
import pathlib
import json
import hashlib
import shutil
import sqlite3
from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
logger = logging.getLogger("uvicorn")
logger.level = logging.INFO
images = pathlib.Path(__file__).parent.resolve() / "images"
sqlite_path = pathlib.Path(__file__).parent.parent.resolve() / "db/mercari.sqlite3"
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
    image_path = images / image.filename
    with open(image_path, "rb") as f:
        # ハッシュ値を取得
        image_hash = hashlib.sha256(f.read()).hexdigest()
    hash_file_name = str(image_hash) + ".jpg"
    upload_dir = open(os.path.join(images / hash_file_name),'wb+')
    shutil.copyfileobj(image.file, upload_dir)

    # sqliteで保存
    con = sqlite3.connect(sqlite_path)
    cur = con.cursor()

    # 新規カテゴリであればcategory_tableに追加
    cur.execute("INSERT INTO category (category) values(?) on conflict (category) do nothing", (category, ))

    # カテゴリIDを取得
    cur.execute("SELECT * FROM category WHERE category = ?", (category, ))
    category_id = cur.fetchone()[0]

    # items_tableに格納
    sql = """INSERT INTO items (name, category_id, image_filename) values(?, ?, ?)"""
    data = (name, category_id, hash_file_name)
    cur.execute(sql, data)
    con.commit()
    con.close()

    logger.info(f"Receive item: {name} (category: {category}, image: {hash_file_name})")
    return {"message": f"item received: {name}"}

@app.get("/items")
def get_item():
    con = sqlite3.connect(sqlite_path)
    cur = con.cursor()
    sql = """
        SELECT items.id, items.name, category.category, items.image_filename FROM items
        INNER JOIN category ON items.category_id = category.id
        """
    cur.execute(sql)
    items = cur.fetchall()
    con.close()

    return items

@app.get("/items/{item_id}")
def get_item_by_id(item_id: int):
    with open('items.json') as f:
        items = json.load(f)
    return items["items"][item_id - 1]

@app.get("/image/{image_filename}")
async def get_image(image_filename):
    # Create image path
    image = images / image_filename

    if not image_filename.endswith(".jpg"):
        raise HTTPException(status_code=400, detail="Image path does not end with .jpg")

    if not image.exists():
        logger.debug(f"Image not found: {image}") #__init__.pyのロギングレベルを15にすると表示される
        image = images / "default.jpg"

    return FileResponse(image)

@app.get("/search")
def get_item_by_keyword(keyword):
    con = sqlite3.connect(sqlite_path)
    cur = con.cursor()
    cur.execute("SELECT * FROM items WHERE name LIKE ?", ("%" + keyword + "%", ))
    #cur.execute("SELECT * FROM items WHERE name LIKE ?", (keyword, ))
    items = cur.fetchall()
    con.close()

    return items