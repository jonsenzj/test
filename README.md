# 🧪 TestGenie — AI 测试用例与脚本生成器

**基于大模型 + RAG 的智能测试效能工具，从需求描述直接生成可执行的自动化测试用例和 pytest 脚本。**

[![GitHub last commit](https://img.shields.io/github/last-commit/jonsenzj/test)](https://github.com/jonsenzj/test)
[![Render](https://img.shields.io/badge/Backend-Render-46E3B7?logo=render)](https://ai-test-generator-y947.onrender.com/docs)
[![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-FF4B4B?logo=streamlit)](你的streamlit地址)

<p align="center">
  <img src="assets/demo.gif" width="700" alt="Demo GIF" />
</p>

---

## ✨ 核心亮点

- 🤖 **需求 → 可执行测试用例**  
  输入自然语言需求，自动生成结构化 JSON 测试用例，并直接生成可运行的 pytest 自动化脚本。

- 🧠 **RAG 检索增强生成**  
  使用 Chroma 向量库 + 智谱 Embedding API，检索历史优质用例作为参考，让生成的测试更贴合业务规范，避免大模型“瞎编”。

- 🎯 **数量精准控制**  
  通过 Prompt 强约束 + 代码层重试与截断，确保输出的用例和脚本数量严格符合要求，解决大模型输出随机性的工程痛点。

- 🌐 **产品级前后端分离**  
  FastAPI 高性能后端提供 RESTful API，Streamlit 构建直观的 Web 交互界面，支持下载用例 JSON 和脚本文件。

- 📊 **历史存储与回溯**  
  SQLite 自动记录每次生成的用例和脚本，侧边栏随时查看历史，方便对比与复用。

- ✅ **真实 API 可执行性验证**  
  使用 [JSONPlaceholder](https://jsonplaceholder.typicode.com) 公开 API 作为被测对象，生成的 pytest 脚本一次跑通，覆盖 CRUD 及异常场景。

- ☁️ **双平台云部署**  
  后端部署于 Render（免费），前端部署于 Streamlit Cloud（免费），24 小时公网可访问，面试演示即开即用。


## 🛠️ 技术栈

| 层次 | 技术 |
|------|------|
| **后端框架** | FastAPI |
| **前端框架** | Streamlit |
| **大模型** | 智谱 GLM-4-Flash (API) |
| **LLM 编排** | LangChain |
| **向量数据库** | Chroma |
| **向量模型** | 智谱 Embedding-2 (API) |
| **关系数据库** | SQLite |
| **自动化测试** | pytest + requests |
| **部署平台** | Render (后端) + Streamlit Cloud (前端) |

---

## 🚀 本地运行

### 1. 环境准备
- Python 3.8+
- 智谱 AI API Key（[免费注册](https://open.bigmodel.cn/)）

### 2. 克隆仓库
```bash
git clone https://github.com/jonsenzj/test.git
cd test

### 3. 安装依赖
```bash
pip install -r requirements.txt

### 4. 配置密钥
在项目根目录创建 .env 文件，写入你的 API Key：
text
ZHIPU_API_KEY=你的key

### 5. 启动后端
```bash
python -m uvicorn app:app --reload
后端运行在 http://127.0.0.1:8000，访问 /docs 可查看 Swagger 文档。

### 6. 启动前端
```bash
streamlit run streamlit_app.py
浏览器自动打开 http://localhost:8501，即可使用完整界面。


