import streamlit as st
import requests
import json
import re

# 本地调试时用 127.0.0.1，部署到 Streamlit Cloud 后改为你的 Render 地址
API_BASE = "http://127.0.0.1:8000"

st.set_page_config(page_title="TestGenie - AI 测试用例生成器", layout="wide")
st.title("🧪 TestGenie - AI 测试用例生成器")

# 侧边栏：历史记录
with st.sidebar:
    st.header("📋 历史记录")
    if st.button("刷新历史"):
        try:
            history = requests.get(f"{API_BASE}/history?limit=20").json()
            for item in history:
                with st.expander(f"{item['requirement'][:30]}... ({item['created_at'][:10]})"):
                    st.text_area("用例", item['cases'], height=200)
                    if item['script']:
                        st.code(item['script'], language='python')
        except Exception as e:
            st.warning(f"无法连接后端: {e}")

# 主界面
col1, col2 = st.columns([2, 1])

with col1:
    requirement = st.text_area("📝 输入需求描述",
                               "用户登录功能：输入用户名和密码，点击登录，成功跳转首页，失败提示错误信息",
                               height=150)
    api_doc = st.text_area("📄 被测接口文档（可选，用于生成更精准的脚本）",
                           "BASE_URL=https://jsonplaceholder.typicode.com\n认证方式：无\n创建帖子 POST /posts, body: {title, body, userId}, 返回 {id, title, body, userId}\n获取列表 GET /posts, 返回数组\n获取详情 GET /posts/{id}, 返回对象或404\n更新 PUT /posts/{id}, 返回更新后的对象\n删除 DELETE /posts/{id}, 返回空对象",
                           height=150)
    num_cases = st.slider("生成用例数量", 1, 10, 5)

    if st.button("🚀 生成测试用例", type="primary"):
        with st.spinner("AI 正在思考..."):
            try:
                # 1. 生成用例
                res = requests.post(f"{API_BASE}/generate-cases",
                                    json={"requirement": requirement, "num_cases": num_cases})
                if res.status_code != 200:
                    st.error(f"生成用例失败: {res.text}")
                else:
                    cases = res.json()["cases"]
                    st.session_state['cases'] = cases
                    st.session_state['requirement'] = requirement
                    st.success(f"成功生成 {len(cases)} 条用例！（请求生成 {num_cases} 条）")

                    for i, case in enumerate(cases, 1):
                        with st.expander(f"用例{i}: {case['title']}", expanded=True):
                            st.markdown(f"**前置条件**: {case.get('precondition', '无')}")
                            steps = case.get('steps', '')
                            if isinstance(steps, list):
                                steps = ' → '.join(steps)
                            st.markdown(f"**测试步骤**: {steps}")
                            st.markdown(f"**预期结果**: {case.get('expected', '')}")

                    # 2. 生成脚本
                    with st.spinner("正在生成 pytest 脚本..."):
                        res2 = requests.post(f"{API_BASE}/generate-script",
                                             json={"cases": cases, "api_doc": api_doc})
                        if res2.status_code != 200:
                            st.error(f"生成脚本失败: {res2.text}")
                        else:
                            script = res2.json()["script"]
                            st.session_state['script'] = script
                            func_count = len(re.findall(r'def (test_\w+)', script))
                            st.success(f"脚本已生成！共 {func_count} 个测试函数（用例数 {len(cases)}）")
                            st.code(script, language='python')
            except Exception as e:
                st.error(f"请求失败: {str(e)}")

with col2:
    st.header("📖 使用说明")
    st.markdown("""
    1. 输入需求描述和被测接口信息
    2. 选择生成数量
    3. 点击生成按钮
    4. 查看用例和脚本
    5. 历史记录自动保存，可下载
    """)
    if 'cases' in st.session_state:
        st.download_button(
            label="📥 下载用例 JSON",
            data=json.dumps(st.session_state['cases'], ensure_ascii=False, indent=2),
            file_name="test_cases.json",
            mime="application/json"
        )
    if 'script' in st.session_state:
        st.download_button(
            label="📥 下载 pytest 脚本",
            data=st.session_state['script'],
            file_name="test_script.py",
            mime="text/x-python"
        )