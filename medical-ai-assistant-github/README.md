# 智能医疗助手（Medical AI Assistant）

一个基于 **FastAPI + LangChain/LangGraph + Vue3/Vite** 的企业级智能医疗助手项目，支持：

- 医疗问答（症状咨询、健康建议、医疗知识检索）
- 预约挂号（多步骤引导、查看预约、取消预约）
- RAG 检索（向量检索 + BM25 + 混合检索 + MMR + 重排）
- SSE 流式输出（前端打字效果）

---

## 1. 项目结构

```text
medical-ai-assistant-github/
├─ app/                         # 后端核心代码（FastAPI + Agent + RAG）
│  ├─ api.py                    # API 入口，SSE 流式对话、预约相关接口
│  ├─ workflow.py               # LangGraph 工作流编排
│  ├─ state.py                  # 全局状态结构定义
│  ├─ agents/                   # 多智能体（意图、症状、知识、处理、安全、回复）
│  ├─ appointment/              # 预约业务（引导、保存、取消、排班 mock）
│  ├─ config/settings.py        # 配置中心（环境变量）
│  ├─ llm/                      # LLM 工厂和提示词
│  ├─ memory/                   # 会话历史存储（JSON 文件）
│  ├─ rag/                      # 检索增强（切片、向量库、检索器、医疗知识文本）
│  └─ utils/                    # 日志、风险词等工具
├─ frontend-vue/                # 前端（Vue3 + Vite）
│  ├─ src/App.vue               # 主页面与交互逻辑
│  ├─ src/style.css             # 企业级 UI 样式
│  ├─ src/main.js               # 前端入口
│  └─ vite.config.js            # 本地代理（/api -> 127.0.0.1:8000）
├─ tests/                       # 测试目录（保留）
├─ requirements.txt             # Python 依赖
├─ .env.example                 # 环境变量模板（请复制为 .env 后修改）
└─ package.json                 # 根目录前端旧构建脚本（主要用 frontend-vue）
```

---

## 2. 技术栈

### 后端
- Python 3.10+
- FastAPI / Uvicorn
- LangChain / LangGraph
- 向量库：FAISS（默认）/ Chroma
- Embedding：HuggingFace（默认 `BAAI/bge-m3`）或 OpenAI/DashScope
- Reranker：`BAAI/bge-reranker-v2-m3`

### 前端
- Vue 3
- Vite
- 原生 CSS（已做企业级医疗 SaaS 风格优化）

---

## 3. 运行前准备

- 安装 Python 3.10+（建议 3.10/3.11）
- 安装 Node.js 18+（建议 18/20）
- 安装 npm（Node 自带）

---

## 4. 环境变量配置

在项目根目录执行：

```bash
cp .env.example .env
```

Windows PowerShell：

```powershell
Copy-Item .env.example .env
```

然后编辑 `.env`，至少配置一组可用模型：

- OpenAI：`OPENAI_API_KEY`
- 或 DashScope：`DASHSCOPE_API_KEY`

并设置：

```env
API_PROVIDER=openai
# 或
API_PROVIDER=dashscope
```

如果你使用本地 embedding（默认）：

```env
EMBEDDING_PROVIDER=huggingface
EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_DEVICE=cpu
```

> 注意：`.env` 不能提交到 GitHub。

---

## 5. 启动后端（FastAPI）

在项目根目录打开终端：

```bash
python -m venv .venv
```

Windows PowerShell 激活虚拟环境：

```powershell
.\.venv\Scripts\Activate.ps1
```

安装依赖：

```bash
pip install -r requirements.txt
```

启动后端：

```bash
python app/api.py
```

默认地址：
- API: http://127.0.0.1:8000
- 文档: http://127.0.0.1:8000/docs

---

## 6. 启动前端（Vue）

新开一个终端，进入前端目录：

```bash
cd frontend-vue
npm install
npm run dev
```

默认地址：
- 前端: http://127.0.0.1:3000

`vite.config.js` 已配置代理：
- `/api/*` 自动转发到 `http://127.0.0.1:8000/*`

---

## 7. 使用说明

1. 打开前端页面
2. 输入医疗咨询问题（支持流式回答）
3. 可通过“预约挂号”进行多步预约
4. 支持“我的预约”“取消预约”“清空会话”
5. 若在预约中切换话题，系统会提示暂停预约流程，可通过“继续预约”恢复

---

## 8. Windows 一键启动（新增）

项目根目录已提供：

- `start-dev.bat`

使用方式（任选其一）：

1. 双击 `start-dev.bat`
2. 或在终端执行：

```bat
start-dev.bat
```

脚本会自动执行：

- 检查 `python` 和 `npm`
- 若无 `.env`，自动由 `.env.example` 复制生成
- 若无 `.venv`，自动创建虚拟环境
- 自动安装后端依赖 `requirements.txt`
- 若前端未安装依赖，自动执行 `npm install`
- 分别打开两个窗口启动：
  - 后端：`http://127.0.0.1:8000`
  - 前端：`http://127.0.0.1:3000`

首次启动前请先在 `.env` 中填写你的 API Key。

---

## 9. 核心 API（简要）

- `POST /chat`：主对话（SSE）
- `GET /history/{session_id}`：获取会话历史
- `POST /clear`：清空会话
- `GET /my-appointments?session_id=...`：我的预约
- `POST /save-appointment`：保存预约
- `POST /cancel-appointment`：取消预约

---

## 10. 常见问题

### 9.1 首次启动慢
原因：embedding/reranker 模型首次下载较慢。首次完成后会快很多。

### 9.2 访问不到前端
确认：
- 前端是否在 `frontend-vue` 目录执行 `npm run dev`
- 后端是否在 `127.0.0.1:8000` 运行

### 9.3 API key 报错
检查 `.env`：
- key 是否正确
- `API_PROVIDER` 是否与 key 对应

### 9.4 Windows 下 HuggingFace symlink 警告
可忽略，不影响功能；或启用开发者模式减少提示。

---

## 11. 生产部署建议

- 使用 Docker 或进程管理器（systemd/supervisor）运行后端
- 前端打包后用 Nginx 托管
- 将 `.env` 放在服务器安全位置，不进入仓库
- 对会话数据与预约数据做备份策略
- 为 API 增加鉴权、限流、审计日志

---

## 12. 安全与隐私

请确保以下内容 **不上传 GitHub**：

- `.env`
- 会话数据目录（如 `sessions/`）
- 向量索引目录（如 `faiss_index/` / `chroma_db/`）
- 本地虚拟环境与缓存目录（`.venv/`、`venv/`、`node_modules/` 等）

---

## 13. 许可证

当前仓库未显式声明许可证（可按需要补充 `LICENSE` 文件）。
