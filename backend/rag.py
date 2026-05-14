from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
# from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
import os

# 第一步：加载 PDF
print("正在加载 PDF...")
loader = PyPDFLoader("test.pdf")
pages = loader.load()
print(f"共加载 {len(pages)} 页")

# 第二步：切分成小块
print("正在切分文本...")
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50
)
chunks = splitter.split_documents(pages)
print(f"共切分成 {len(chunks)} 个块")

# 第三步：转成向量存入数据库
print("正在生成向量并存入数据库（第一次较慢）...")
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
db = Chroma.from_documents(chunks, embeddings, persist_directory="./chroma_db")
print("向量数据库建立完成！")

# 第四步：测试检索
query = "What is the selfish gene"
print(f"\n测试检索：{query}")
results = db.similarity_search(query, k=3)
for i, doc in enumerate(results):
    print(f"\n--- 第{i+1}条相关内容 ---")
    print(doc.page_content[:200])


from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

# 把检索到的内容拼成上下文
context = "\n\n".join([doc.page_content for doc in results])

# 构建发给 AI 的提示词
prompt = f"""请根据以下书中的内容回答用户的问题。

书中相关内容：
{context}

用户问题：{query}

请用中文回答，只根据上面提供的内容作答。"""

print("\n--- AI 回答 ---")
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": prompt}]
)
print(response.choices[0].message.content)