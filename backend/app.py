from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from langchain_core import messages
from pydantic import BaseModel
from openai import OpenAI
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
import os
import shutil
from typing import TypedDict
from langgraph.graph import StateGraph, END, START

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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

# State定义
class State(TypedDict):
    question: str
    documents: list
    answer: str
    is_relevant: bool
    history: list

# 节点一：检索
def retrieve(state: State):
    results = db.similarity_search(state["question"], k=3)
    return {"documents": results}

# 节点二：判断相关性
def check_relevance(state: State):
    if not state["documents"]:
        return {"is_relevant": False}
    context = state["documents"][0].page_content[:200]
    prompt = f"问题：{state['question']}\n文档片段：{context}\n这个文档片段和问题相关吗？只回答yes或no。"
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}]
    )
    answer = response.choices[0].message.content.strip().lower()
    return {"is_relevant": "yes" in answer}

# 节点三：生成答案
def generate(state: State):
    context = "\n\n".join([doc.page_content for doc in state["documents"]])

    # 构建带历史的消息列表
    messages = []

    #加入历史对话
    for turn in state.get("history", []):
        messages.append({"role": "user", "content": turn["question"]})
        messages.append({"role": "assistant", "content": turn["answer"]})

    # 加入当前问题和文档
    prompt = f"""Please answer the question based on the document content.

    Document content:
    {context}

    Question: {state['question']}

    Please answer in English, based only on the content provided. Consider the conversation history for context."""

    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages
    )
    return {
        "answer": response.choices[0].message.content
    }

# 节点四：无相关内容
def no_answer(state: State):
    return {"answer": "Sorry, I couldn't find relevant information in the document to answer your question."}

# 条件路由
def route(state: State):
    return "generate" if state["is_relevant"] else "no_answer"

# 构建图
def build_graph():
    graph = StateGraph(State)
    graph.add_node("retrieve", retrieve)
    graph.add_node("check_relevance", check_relevance)
    graph.add_node("generate", generate)
    graph.add_node("no_answer", no_answer)
    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "check_relevance")
    graph.add_conditional_edges("check_relevance", route)
    graph.add_edge("generate", END)
    graph.add_edge("no_answer", END)
    return graph.compile()

rag_app = build_graph()

# 请求体
class Question(BaseModel):
    question: str
    history: list = []

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

    result = rag_app.invoke({
        "question": q.question,
        "documents": [],
        "answer": "",
        "is_relevant": False,
        "history": q.history
    })

    sources = list(set([
        doc.metadata.get("page", 0) + 1
        for doc in result["documents"]
    ])) if result["documents"] else []

    return {
        "answer": result["answer"],
        "sources": sources if result["is_relevant"] else []
    }