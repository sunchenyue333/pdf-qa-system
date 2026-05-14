from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
import os
import shutil

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

db = None

# 请求体
class Question(BaseModel):
    question: str

# 上传 PDF
@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    global db

    # 保存上传的文件
    file_path = f"./uploads/{file.filename}"
    os.makedirs("uploads", exist_ok=True)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # 加载、切分、存向量库
    loader = PyPDFLoader(file_path)
    pages = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(pages)
    db = Chroma.from_documents(chunks, embeddings, persist_directory="./chroma_db")

    return {"message": f"Successfully processed {len(pages)} pages，{len(chunks)} chunks"}

# 提问
@app.post("/ask")
async def ask(q: Question):
    if db is None:
        return {"answer": "Please upload a PDF file first", "sources": []}

    results = db.similarity_search(q.question, k=3)
    context = "\n\n".join([doc.page_content for doc in results])

    # 提取来源页码
    sources = []
    for doc in results:
        page = doc.metadata.get("page", 0) + 1  # PDF页码从0开始，+1变成自然页码
        if page not in sources:
            sources.append(page)

    prompt = f"""Please answer the user's question based on the following document content.

    Document content：
    {context}

    User question：{q.question}

    Please answer in English, based only on the content provided above。"""

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}]
    )

    return {
        "answer": response.choices[0].message.content,
        "sources": sources
    }