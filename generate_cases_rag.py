import os
import json
import re
from openai import OpenAI
from dotenv import load_dotenv

# LangChain 相关
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter          # 这行改了
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
# ========== 1. 加载环境变量 ==========
load_dotenv()
api_key = os.getenv("ZHIPU_API_KEY")

# 初始化智谱客户端
client = OpenAI(
    api_key=api_key,
    base_url="https://open.bigmodel.cn/api/paas/v4/"
)

# ========== 2. 准备向量数据库（加载知识库） ==========
print("正在初始化知识库（仅第一次会下载模型，稍等）...")

# 读取我们写好的历史用例文件
loader = TextLoader("test_cases_knowledge.txt", encoding="utf-8")
documents = loader.load()

# 把长文档切成小段，每段 500 字，重叠 50 字，避免切断一条完整用例
text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)
docs = text_splitter.split_documents(documents)

# 使用免费的 HuggingFace 中文向量模型，把文本变成向量
# 第一次运行会自动下载模型，大约几百MB
embedding_model = HuggingFaceEmbeddings(model_name="shibing624/text2vec-base-chinese")

# 创建 Chroma 向量库，数据存到本地的 chroma_db 文件夹
vectordb = Chroma.from_documents(
    documents=docs,
    embedding=embedding_model,
    persist_directory="chroma_db"
)
print("知识库初始化完成！\n")

# ========== 3. 检索相关历史用例 ==========
def search_similar_cases(requirement_text, k=3):
    """根据需求文本，从知识库里检索最相似的 k 条用例"""
    results = vectordb.similarity_search(requirement_text, k=k)
    return [doc.page_content for doc in results]

# ========== 4. 还是那个提取 JSON 的工具函数 ==========
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

# ========== 5. 主流程：检索 + 生成 ==========
requirement = "用户登录功能：输入用户名和密码，点击登录，成功跳转首页，失败提示错误信息"

# 从知识库检索相关历史用例
similar_cases = search_similar_cases(requirement, k=3)
print("检索到以下相似历史用例作为参考：")
for i, case in enumerate(similar_cases, 1):
    print(f"--- 参考用例 {i} ---")
    print(case)
    print()

# 把这些历史用例拼成字符串，放进 Prompt 里
reference_text = "\n\n".join(similar_cases)

prompt = f"""
你是一个资深测试工程师。请参考下面的【历史优秀测试用例】，为给定的新需求生成 5 条详细的测试用例。

【历史优秀测试用例】
{reference_text}

【新需求】
{requirement}

要求：
1. 每条用例包含：用例标题、前置条件、测试步骤、预期结果。
2. 模仿历史用例的粒度、描述风格和覆盖场景。
3. 输出格式为严格的 JSON 列表，每个元素是一个字典，包含 title, precondition, steps, expected 字段。
4. 直接输出 JSON，不要有任何其他文字，也不要使用代码块标记。
"""

print("正在让 AI 基于参考生成测试用例...\n")
response = client.chat.completions.create(
    model="glm-4-flash",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.3
)

raw_result = response.choices[0].message.content
print("===== AI 返回 =====")
print(raw_result)
print("==================\n")

# 解析并保存
cases = extract_json(raw_result)
if cases is None:
    print("❌ 无法解析出 JSON")
    exit(1)

print(f"成功生成 {len(cases)} 条用例：")
for i, case in enumerate(cases, 1):
    print(f"\n用例{i}: {case['title']}")
    print(f"  前置条件: {case['precondition']}")
    steps = case['steps']
    if isinstance(steps, list):
        steps_text = " -> ".join(steps)
    else:
        steps_text = steps
    print(f"  步骤: {steps_text}")
    print(f"  预期: {case['expected']}")

# 保存到文件
with open("generated_cases_rag.json", "w", encoding="utf-8") as f:
    json.dump(cases, f, ensure_ascii=False, indent=2)
    print("\n✅ 已保存到 generated_cases_rag.json")