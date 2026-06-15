# ZhiDo / MADF 多智能体圆桌平台

ZhiDo 是一个基于 Vue 3 + FastAPI 的多智能体圆桌讨论平台，支持智能体对话、论坛讨论、时空之门式的一对一聊天，以及图片上传和流式回复。

## 主要功能

- 多智能体圆桌讨论
- 时空之门对话页
- 图片上传后参与对话
- 流式输出回复
- 用户认证、智能体管理、论坛管理
- 本地开发与 Docker 部署

## 技术栈

- 前端：Vue 3、TypeScript、Vite、Pinia、Vue Router、Ant Design Vue
- 后端：FastAPI、Uvicorn
- 数据库：SQLite
- 缓存：Redis（可选）
- 测试：Vitest、Cypress、Pytest

## 快速开始

### 1. 配置环境变量

在项目根目录创建 `.env`，至少配置以下变量：

```ini
API_KEY=your_llm_api_key
MODEL_NAME=glm-4.5
BASE_URL=https://open.bigmodel.cn/api/paas/v4/
SECRET_KEY=your_secret_key
DATABASE_URL=file:madf.db
REDIS_URL=redis://localhost:6379/0
```

说明：

- `API_KEY` 是模型服务密钥，必须设置。
- `MODEL_NAME` 默认使用 `glm-4.5`，如果你的账号支持，也可以改成 `glm-4.6`。
- `BASE_URL` 默认指向智谱开放平台接口地址。
- `SECRET_KEY` 建议设置为足够长的随机字符串。

### 2. 本地启动后端

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 本地启动前端

```bash
cd frontend
npm install
npm run dev
```

访问地址：

- 前端：`http://localhost:5173`
- 后端 API：`http://localhost:8000/api/v1`

### 4. Docker 启动

```bash
docker compose up -d --build
```

Docker Compose 会使用根目录的 `docker-compose.yml`，并暴露 `8000` 端口。

## 常用命令

```bash
# 后端
python -m pytest

# 前端
cd frontend
npm run type-check
npx cypress run --browser electron --spec 'cypress/e2e/time_gate_smoke.cy.ts'
```

## 项目结构

```text
app/           后端 FastAPI 代码
frontend/      前端 Vue 代码
docs/          部署和设计文档
uploads/       上传文件目录
docker-compose.yml
requirements.txt
```

## 部署说明

- 生产环境建议使用 Docker Compose 或单独的 Uvicorn + Nginx 方案。
- 图片上传文件由后端通过 `/uploads` 静态目录提供。
- 如果你在本地开发中修改了模型配置，确保 `.env` 中的 `API_KEY`、`MODEL_NAME`、`BASE_URL` 与实际可用服务一致。

## 许可证

MIT
