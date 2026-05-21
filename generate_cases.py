import os
import json
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("ZHIPU_API_KEY")

client = OpenAI(
    api_key=api_key,
    base_url="https://open.bigmodel.cn/api/paas/v4/"
)

# ========== 新增：提取 JSON 的通用函数 ==========
def extract_json(text):
    """
    从 LLM 返回的文本中提取 JSON，无论是否被 ```json 包裹。
    返回 Python 对象（list/dict），提取失败则返回 None。
    """
    # 尝试直接解析整个文本
    try:
        return json.loads(text)
    except:
        pass

    # 尝试匹配 ```json ... ``` 里的内容
    match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            pass

    # 尝试匹配 { 或 [ 开始的 JSON 内容（贪心截取）
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


# 原来的需求描述，不变
requirement = "用户登录功能：输入用户名和密码，点击登录，成功跳转首页，失败提示错误信息"

prompt = f"""
你是一个资深测试工程师。请根据下面的需求，生成 5 条详细的测试用例。

需求：
{requirement}

要求：
1. 每条用例包含：用例标题、前置条件、测试步骤、预期结果。
2. 输出格式为严格的 JSON 列表，每个元素是一个字典，包含 title, precondition, steps, expected 字段。
3. 直接输出 JSON，不要有任何其他文字，也不要使用代码块标记。
"""

print("正在让 AI 生成测试用例...\n")
response = client.chat.completions.create(
    model="glm-4-flash",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.3
)

raw_result = response.choices[0].message.content
print("===== AI 原始返回 =====")
print(raw_result)
print("=======================\n")

# ========== 新增：解析 JSON ==========
cases = extract_json(raw_result)
if cases is None:
    print("❌ 无法解析出 JSON，请检查 Prompt 或重试")
    exit(1)

# 打印看看效果
print(f"成功解析出 {len(cases)} 条用例：")
for i, case in enumerate(cases, 1):
    print(f"\n用例{i}: {case['title']}")
    print(f"  前置条件: {case['precondition']}")
    # steps 可能是字符串或列表，统一处理
    steps = case['steps']
    if isinstance(steps, list):
        steps_text = " -> ".join(steps)
    else:
        steps_text = steps
    print(f"  步骤: {steps_text}")
    print(f"  预期: {case['expected']}")

# ========== 新增：把结果保存到文件 ==========
with open("generated_cases.json", "w", encoding="utf-8") as f:
    json.dump(cases, f, ensure_ascii=False, indent=2)
    print("\n✅ 已保存到 generated_cases.json")