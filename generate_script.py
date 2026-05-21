import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("ZHIPU_API_KEY")

client = OpenAI(
    api_key=api_key,
    base_url="https://open.bigmodel.cn/api/paas/v4/"
)

# 读取之前生成的用例
with open("generated_cases_rag.json", "r", encoding="utf-8") as f:
    cases = json.load(f)

# 把用例内容拼成一段文字描述
cases_text = ""
for i, case in enumerate(cases, 1):
    cases_text += f"""
用例{i}: {case['title']}
前置条件: {case['precondition']}
步骤: {case['steps'] if isinstance(case['steps'], str) else ' -> '.join(case['steps'])}
预期: {case['expected']}
"""

prompt = f"""
你是一个自动化测试专家。请根据以下测试用例，用 Python 的 pytest 框架编写自动化测试脚本。

要求：
1. 每个用例写成一个独立的测试函数，函数名以 test_ 开头。
2. 使用 requests 库模拟接口调用（假设被测接口为 http://localhost:5000/login，请求体为 JSON 格式：{{"username": "...", "password": "..."}}，返回格式为 {{"message": "...", "code": 200/401}}）。
3. 根据用例的预期结果，编写对应的 assert 断言。
4. 给出完整可运行的代码，包含必要的 import 和 fixture（如需要）。
5. 直接输出 Python 代码，不要用 markdown 代码块包裹，也不要多余说明。

测试用例列表：
{cases_text}
"""

print("正在让 AI 生成 pytest 脚本...\n")
response = client.chat.completions.create(
    model="glm-4-flash",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.2   # 更低温度，让代码更确定
)

script = response.choices[0].message.content

# 清理可能出现的 markdown 包裹
if script.startswith("```python"):
    script = script.split("```python")[1]
if "```" in script:
    script = script.split("```")[0]

print("===== 生成的测试脚本 =====")
print(script)
print("==========================\n")

# 保存为 .py 文件
with open("test_generated.py", "w", encoding="utf-8") as f:
    f.write(script)

print("✅ 已保存为 test_generated.py")
print("你可以用命令 pytest test_generated.py -v 运行（需要 pip install pytest requests）")