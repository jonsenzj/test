import os
import json
import re
import sqlite3
import datetime
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

# ========== 向量库初始化（智能判断：存在则加载，不存在则创建）==========
print("正在加载知识库...")
persist_dir = "chroma_db"

embedding_model = OpenAIEmbeddings(
    model="embedding-2",
    openai_api_key=api_key,
    openai_api_base="https://open.bigmodel.cn/api/paas/v4/"
)

if not os.path.exists(persist_dir):
    loader = TextLoader("test_cases_knowledge.txt", encoding="utf-8")
    documents = loader.load()
    text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs = text_splitter.split_documents(documents)
    vectordb = Chroma.from_documents(
        documents=docs,
        embedding=embedding_model,
        persist_directory=persist_dir
    )
    print("知识库首次创建完成。")
else:
    vectordb = Chroma(
        persist_directory=persist_dir,
        embedding_function=embedding_model
    )
    print("知识库加载完成（使用已有 chroma_db）。")

# ========== SQLite 初始化 ==========
def init_db():
    conn = sqlite3.connect('testgenie.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  requirement TEXT,
                  cases TEXT,
                  script TEXT,
                  created_at TEXT)''')
    conn.commit()
    conn.close()

init_db()

def save_to_db(requirement, cases_json, script):
    conn = sqlite3.connect('testgenie.db')
    c = conn.cursor()
    c.execute("INSERT INTO history (requirement, cases, script, created_at) VALUES (?, ?, ?, ?)",
              (requirement, cases_json, script, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_history(limit=20):
    conn = sqlite3.connect('testgenie.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM history ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return rows

# ========== FastAPI 应用 ==========
app = FastAPI(title="AI 测试用例生成器", version="2.0")

class RequirementInput(BaseModel):
    requirement: str
    num_cases: int = 5

class ScriptGenerationRequest(BaseModel):
    cases: list
    api_doc: str = ""

def search_similar_cases(requirement_text, k=3):
    results = vectordb.similarity_search(requirement_text, k=k)
    return [doc.page_content for doc in results]

def extract_json(text):
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

@app.post("/generate-cases")
def generate_cases(req: RequirementInput):
    similar = search_similar_cases(req.requirement)
    reference_text = "\n\n".join(similar)
    prompt = f"""
你是一个资深测试工程师。请参考下面的【历史优秀测试用例】，为给定的新需求生成正好{req.num_cases}条详细的测试用例，不能多也不能少。

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
    # 重试 + 截断
    for attempt in range(3):
        response = client.chat.completions.create(
            model="glm-4-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        raw = response.choices[0].message.content
        cases = extract_json(raw)
        if cases is None:
            continue
        if isinstance(cases, list) and len(cases) >= req.num_cases:
            cases = cases[:req.num_cases]  # 多了截断
            break
        elif isinstance(cases, list) and len(cases) < req.num_cases:
            prompt += f"\n\n注意：上次你只生成了{len(cases)}条，请严格生成正好{req.num_cases}条。"
    else:
        if cases is None:
            raise HTTPException(status_code=500, detail="无法解析生成的 JSON")
        if isinstance(cases, list):
            cases = cases[:req.num_cases]
        else:
            raise HTTPException(status_code=500, detail="生成格式错误")

    save_to_db(req.requirement, json.dumps(cases, ensure_ascii=False), "")
    return {"cases": cases}

@app.post("/generate-script")
def generate_script(req: ScriptGenerationRequest):
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
    base_prompt = f"""
你是一个自动化测试专家。请严格根据下面的【测试用例列表】编写 pytest 自动化测试脚本。

硬性要求：
- 必须为列表中的每一条用例写一个对应的测试函数，函数名以 test_ 开头。
- 测试函数的总数量必须严格等于{len(req.cases)}个，绝对不能多或少。
- 绝对不要添加任何列表中没有的用例，比如登录、认证等场景。
- 只使用 requests 库，根据预期结果进行断言。
- 直接输出 Python 代码，不要包含 markdown 标记，也不要解释文字。

"""
    if req.api_doc:
        base_prompt = f"被测接口文档摘要：\n{req.api_doc}\n\n" + base_prompt
    base_prompt += f"\n测试用例列表：\n{cases_text}"

    max_retries = 2
    script = ""
    for attempt in range(max_retries + 1):
        response = client.chat.completions.create(
            model="glm-4-flash",
            messages=[{"role": "user", "content": base_prompt}],
            temperature=0.1
        )
        raw_script = response.choices[0].message.content
        if raw_script.startswith("```python"):
            raw_script = raw_script.split("```python")[1]
        if "```" in raw_script:
            raw_script = raw_script.split("```")[0]
        script = raw_script.strip()

        funcs = re.findall(r'^def (test_\w+)', script, re.MULTILINE)
        if len(funcs) == len(req.cases):
            break
        elif attempt < max_retries:
            base_prompt += f"\n\n错误：上次生成的脚本有{len(funcs)}个测试函数，但需要正好{len(req.cases)}个。请删除多余的，并补充缺失的。"
    else:
        # 最终兜底：如果函数多了，截断
        funcs = re.findall(r'^def (test_\w+)', script, re.MULTILINE)
        if len(funcs) > len(req.cases):
            parts = re.split(r'(?=^def test_)', script, flags=re.MULTILINE)
            header = parts[0]
            selected = [p for p in parts[1:] if p.startswith('def test_')][:len(req.cases)]
            script = header + '\n'.join(selected)

    # 更新数据库
    conn = sqlite3.connect('testgenie.db')
    c = conn.cursor()
    c.execute("UPDATE history SET script = ? WHERE id = (SELECT MAX(id) FROM history)", (script,))
    conn.commit()
    conn.close()

    return {"script": script}

@app.get("/history")
def history(limit: int = 20):
    return get_history(limit)

@app.get("/")
def root():
    return {"message": "AI 测试用例生成服务已运行。使用 /docs 查看接口文档。"}