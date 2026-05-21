import os
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

# RAG 相关
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

load_dotenv()
api_key = os.getenv("ZHIPU_API_KEY")

client = OpenAI(
    api_key=api_key,
    base_url="https://open.bigmodel.cn/api/paas/v4/"
)

# 初始化向量库（启动时做一次，后续复用）
print("加载知识库...")
loader = TextLoader("test_cases_knowledge.txt", encoding="utf-8")
documents = loader.load()
text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)
docs = text_splitter.split_documents(documents)

embedding_model = OpenAIEmbeddings(
    model="embedding-2",
    openai_api_key=api_key,
    openai_api_base="https://open.bigmodel.cn/api/paas/v4/"
)
vectordb = Chroma.from_documents(
    documents=docs,
    embedding=embedding_model,
    persist_directory="chroma_db"
)
print("知识库加载完成。")

app = FastAPI(title="AI 测试用例生成器", version="1.0")

# 请求模型
class RequirementInput(BaseModel):
    requirement: str
    num_cases: int = 5  # 可指定生成条数

class CasesInput(BaseModel):
    cases: list

def search_similar_cases(requirement_text, k=3):
    results = vectordb.similarity_search(requirement_text, k=k)
    return [doc.page_content for doc in results]

def extract_json(text):
    import re
    try:
        return json.loads(text)
    except:
        pass
    match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            pass
    for start_char in ['[', '{']:
        start = text.find(start_char)
        if start != -1:
            end_char = ']' if start_char == '[' else '}'
            end = text.rfind(end_char)
            if end != -1:
                try:
                    return json.loads(text[start:end+1])
                except:
                    continue
    return None

# 接口1：生成测试用例（基于 RAG）
@app.post("/generate-cases")
def generate_cases(req: RequirementInput):
    # 检索相似用例
    similar = search_similar_cases(req.requirement)
    reference_text = "\n\n".join(similar)

    prompt = f"""
你是一个资深测试工程师。请参考下面的【历史优秀测试用例】，为给定的新需求生成{req.num_cases}条详细的测试用例。

【历史优秀测试用例】
{reference_text}

【新需求】
{req.requirement}

要求：
1. 每条用例包含：用例标题、前置条件、测试步骤、预期结果。
2. 模仿历史用例的粒度、描述风格和覆盖场景。
3. 输出格式为严格的 JSON 列表，每个元素是一个字典，包含 title, precondition, steps, expected 字段。
4. 直接输出 JSON，不要有任何其他文字，也不要使用代码块标记。
"""

    response = client.chat.completions.create(
        model="glm-4-flash",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    raw = response.choices[0].message.content
    cases = extract_json(raw)
    if cases is None:
        raise HTTPException(status_code=500, detail="无法解析生成的 JSON")
    return {"cases": cases}

# 接口2：生成 pytest 脚本
@app.post("/generate-script")
def generate_script(req: CasesInput):
    # 构造用例描述文本
    cases_text = ""
    for i, case in enumerate(req.cases, 1):
        steps = case.get('steps', '')
        if isinstance(steps, list):
            steps = ' -> '.join(steps)
        cases_text += f"""
用例{i}: {case.get('title','')}
前置条件: {case.get('precondition','')}
步骤: {steps}
预期: {case.get('expected','')}
"""
    prompt = f"""
你是一个自动化测试专家。请根据以下测试用例，用 Python 的 pytest 框架编写自动化测试脚本。

要求：
1. 每个用例写成一个独立的测试函数，函数名以 test_ 开头。
2. 使用 requests 库模拟接口调用（假设被测接口为 http://localhost:5000/login，请求体为 JSON 格式：{{"username": "...", "password": "..."}}，返回格式为 {{"message": "...", "code": 200/401}}）。
3. 根据用例的预期结果，编写对应的 assert 断言。
4. 给出完整可运行的代码，包含必要的 import 和 fixture。
5. 直接输出 Python 代码，不要用 markdown 代码块包裹，也不要多余说明。

测试用例列表：
{cases_text}
"""
    response = client.chat.completions.create(
        model="glm-4-flash",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    script = response.choices[0].message.content
    # 简单清理
    if script.startswith("```python"):
        script = script.split("```python")[1]
    if "```" in script:
        script = script.split("```")[0]
    return {"script": script.strip()}

# 根路径
@app.get("/")
def root():
    return {"message": "AI 测试用例生成服务已运行。使用 /docs 查看接口文档。"}