# 腾讯云轻量服务器部署指南

本文档适用于将 ZhiDo / MADF 部署到腾讯云轻量服务器或同类 Linux 服务器。

## 1. 部署前准备

- 一台已安装 Ubuntu 22.04 的云服务器
- 一个可用的域名，可选
- 已准备好的模型服务 `API_KEY`
- 开放端口：`8000`，如果要接入域名和 HTTPS，还需要开放 `80` 和 `443`

## 2. 安装基础环境

### 2.1 更新系统

```bash
sudo apt update
sudo apt upgrade -y
```

### 2.2 安装 Docker

```bash
sudo apt install -y ca-certificates curl gnupg lsb-release
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable docker
sudo systemctl start docker
```

## 3. 获取代码

```bash
sudo mkdir -p /opt/zido
cd /opt/zido
git clone <你的仓库地址> .
```

如果是手动上传代码，确保项目根目录下包含 `docker-compose.yml`、`requirements.txt` 和 `frontend/`。

## 4. 配置环境变量

在项目根目录创建 `.env`：

```ini
API_KEY=your_llm_api_key
MODEL_NAME=glm-4.5
BASE_URL=https://open.bigmodel.cn/api/paas/v4/
SECRET_KEY=your_secret_key
DATABASE_URL=file:/app/data/madf.db
REDIS_URL=redis://localhost:6379/0
```

建议：

- `SECRET_KEY` 至少使用 32 位以上随机字符串
- 如果你的账号支持，也可以把 `MODEL_NAME` 改成 `glm-4.6`

## 5. 启动服务

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f
```

服务启动后：

- 后端健康检查：`http://服务器IP:8000/api/v1/health`
- 前端页面：`http://服务器IP:8000`

## 6. 可选：Nginx 反向代理

如果要使用域名和 HTTPS，可以在前面再加一层 Nginx：

```nginx
server {
    listen 80;
    server_name your.domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 7. 常见问题

### 7.1 页面打不开

- 检查 `8000` 端口是否放行
- 检查 Docker 容器是否正常运行
- 查看 `docker compose logs -f`

### 7.2 模型调用失败

- 确认 `.env` 中的 `API_KEY` 正确
- 确认 `BASE_URL` 和 `MODEL_NAME` 与实际可用服务匹配

### 7.3 上传图片失败

- 检查 `uploads/` 目录是否可写
- 检查浏览器和后端是否指向同一套服务

*** Delete File: D:/Users/Lenovo/Desktop/专家圆桌会议/ZhiDo V1.1.0/启动项目.md
