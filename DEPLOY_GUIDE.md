# 腾讯云轻量服务器部署指南

本指南将帮助您将 MADF（多智能体讨论框架）部署到腾讯云轻量应用服务器。

## 目录

1. [准备工作](#1-准备工作)
2. [连接服务器](#2-连接服务器)
3. [安装 Docker](#3-安装-docker)
4. [部署应用](#4-部署应用)
5. [配置域名解析](#5-配置域名解析)
6. [配置 Nginx 反向代理](#6-配置-nginx-反向代理)
7. [配置 HTTPS 证书](#7-配置-https-证书)
8. [常见问题](#8-常见问题)

---

## 1. 准备工作

### 1.1 购买腾讯云轻量应用服务器

1. 访问 [腾讯云轻量应用服务器](https://cloud.tencent.com/product/lighthouse)
2. 点击「立即购买」
3. 选择配置：
   - **地域**：选择离您用户最近的地区（如广州、上海、北京）
   - **镜像**：选择 **Ubuntu 22.04 LTS**
   - **套餐**：建议选择 **2核4G** 或以上配置（AI应用需要一定内存）
   - **时长**：根据需求选择
4. 完成购买

### 1.2 获取服务器信息

购买完成后，在控制台获取以下信息：
- **公网IP**：如 `123.45.67.89`
- **用户名**：默认为 `root` 或 `ubuntu`
- **密码**：购买时设置的密码（如忘记可重置）

---

## 2. 连接服务器

### 2.1 Windows 用户（使用 PowerShell 或终端）

```bash
# 替换为您的服务器公网IP
ssh root@123.45.67.89

# 如果用户名是 ubuntu
ssh ubuntu@123.45.67.89
```

首次连接会提示确认指纹，输入 `yes` 然后输入密码即可登录。

### 2.2 首次登录建议

登录后，建议先更新系统：

```bash
# 更新软件包列表
sudo apt update

# 升级已安装的软件包
sudo apt upgrade -y
```

---

## 3. 安装 Docker

### 3.1 安装 Docker

```bash
# 安装必要的依赖
sudo apt install -y ca-certificates curl gnupg lsb-release

# 添加 Docker 官方 GPG 密钥
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# 添加 Docker 软件源
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装 Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 启动 Docker 服务
sudo systemctl start docker
sudo systemctl enable docker

# 验证安装
sudo docker --version
sudo docker compose version
```

### 3.2 配置 Docker 镜像加速（国内服务器推荐）

```bash
# 创建配置目录
sudo mkdir -p /etc/docker

# 配置镜像加速
sudo tee /etc/docker/daemon.json <<-'EOF'
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ]
}
EOF

# 重启 Docker 服务
sudo systemctl daemon-reload
sudo systemctl restart docker
```

---

## 4. 部署应用

### 4.1 创建项目目录

```bash
# 创建应用目录
sudo mkdir -p /opt/madf
cd /opt/madf
```

### 4.2 创建环境配置文件

```bash
# 创建 .env 文件
sudo nano .env
```

在编辑器中输入以下内容（替换您的 API Key）：

```env
# LLM API Configuration
API_KEY=您的智谱AI_API_Key
MODEL_NAME=glm-4.5
BASE_URL=https://open.bigmodel.cn/api/paas/v4/

# Search API Configuration（可选）
SERPAPI_API_KEY=your_serpapi_key

# Database
DATABASE_URL=file:/app/data/madf.db
```

按 `Ctrl + O` 保存，按 `Ctrl + X` 退出。

### 4.3 创建 docker-compose.yml 文件

```bash
sudo nano docker-compose.yml
```

输入以下内容：

```yaml
version: '3.8'

services:
  madf:
    image: frozenfish717/madf:latest
    container_name: madf-app
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=file:/app/data/madf.db
      - REDIS_URL=redis://localhost:6379/0
      - PYTHONPATH=/app
      - API_KEY=${API_KEY}
      - MODEL_NAME=${MODEL_NAME:-glm-4.5}
      - BASE_URL=${BASE_URL:-https://open.bigmodel.cn/api/paas/v4/}
    volumes:
      - madf_data:/app/data
    restart: always

volumes:
  madf_data:
```

### 4.4 启动应用

```bash
# 拉取镜像并启动
sudo docker compose up -d

# 查看运行状态
sudo docker compose ps

# 查看日志
sudo docker compose logs -f
```

### 4.5 验证部署

在浏览器中访问：`http://您的服务器公网IP:8000`

如果看到登录页面，说明部署成功！

---

## 5. 配置域名解析

### 5.1 添加 DNS 解析记录

1. 登录腾讯云控制台
2. 进入「域名注册」→「我的域名」
3. 点击域名后的「解析」
4. 添加记录：

| 记录类型 | 主机记录 | 记录值 | TTL |
|---------|---------|--------|-----|
| A | @ | 您的服务器公网IP | 600 |
| A | www | 您的服务器公网IP | 600 |

例如：
- 主机记录：`@`（代表根域名 `example.com`）
- 记录值：`123.45.67.89`（您的服务器IP）

### 5.2 等待解析生效

DNS 解析通常需要 10 分钟到 2 小时生效。可以用以下命令验证：

```bash
# 在本地电脑执行
ping 您的域名.com
```

如果返回的是您的服务器IP，说明解析已生效。

---

## 6. 配置 Nginx 反向代理

### 6.1 安装 Nginx

```bash
sudo apt install -y nginx
```

### 6.2 创建站点配置

```bash
sudo nano /etc/nginx/sites-available/madf
```

输入以下内容（替换您的域名）：

```nginx
server {
    listen 80;
    server_name 您的域名.com www.您的域名.com;

    # 日志
    access_log /var/log/nginx/madf.access.log;
    error_log /var/log/nginx/madf.error.log;

    # 反向代理到 Docker 容器
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持
        proxy_read_timeout 86400;
    }

    # 上传文件大小限制
    client_max_body_size 100M;
}
```

### 6.3 启用站点配置

```bash
# 创建软链接
sudo ln -s /etc/nginx/sites-available/madf /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重载 Nginx
sudo systemctl reload nginx
```

### 6.4 验证

现在可以通过 `http://您的域名.com` 访问应用了！

---

## 7. 配置 HTTPS 证书

### 7.1 安装 Certbot

```bash
sudo apt install -y certbot python3-certbot-nginx
```

### 7.2 申请 SSL 证书

```bash
# 替换您的域名
sudo certbot --nginx -d 您的域名.com -d www.您的域名.com
```

按提示操作：
1. 输入您的邮箱地址（用于接收证书到期提醒）
2. 同意服务条款（输入 `Y`）
3. 是否接收营销邮件（可选 `N`）
4. 选择是否重定向 HTTP 到 HTTPS（推荐选择 `2` 重定向）

### 7.3 自动续期

Certbot 会自动设置定时任务续期，可以测试：

```bash
# 测试续期
sudo certbot renew --dry-run
```

### 7.4 验证 HTTPS

现在可以通过 `https://您的域名.com` 访问应用了！

---

## 8. 常见问题

### 8.1 端口无法访问

**问题**：访问 `http://IP:8000` 无响应

**解决方案**：检查防火墙设置

```bash
# 查看防火墙状态
sudo ufw status

# 开放必要端口
sudo ufw allow 22      # SSH
sudo ufw allow 80      # HTTP
sudo ufw allow 443     # HTTPS
sudo ufw allow 8000    # 应用端口（可选，Nginx代理后可关闭）

# 启用防火墙
sudo ufw enable
```

**腾讯云安全组**：还需要在腾讯云控制台配置安全组规则，放行 80、443、8000 端口。

### 8.2 Docker 容器无法启动

**问题**：`docker compose up -d` 后容器状态异常

**解决方案**：查看日志排查

```bash
# 查看容器日志
sudo docker compose logs

# 查看详细状态
sudo docker compose ps
```

### 8.3 域名无法访问

**问题**：域名解析正确但无法访问

**解决方案**：

1. 检查 Nginx 配置：
```bash
sudo nginx -t
sudo systemctl status nginx
```

2. 检查 DNS 解析：
```bash
nslookup 您的域名.com
```

### 8.4 HTTPS 证书申请失败

**问题**：Certbot 申请证书失败

**解决方案**：

1. 确保域名已正确解析到服务器
2. 确保 80 端口可访问
3. 检查 Nginx 配置是否正确

### 8.5 更新应用

```bash
cd /opt/madf

# 拉取最新镜像
sudo docker compose pull

# 重新部署
sudo docker compose up -d
```

### 8.6 查看应用日志

```bash
# 实时查看日志
sudo docker compose logs -f

# 查看最近 100 行日志
sudo docker compose logs --tail=100
```

### 8.7 重启应用

```bash
cd /opt/madf
sudo docker compose restart
```

---

## 9. 维护命令速查

| 操作 | 命令 |
|------|------|
| 启动应用 | `sudo docker compose up -d` |
| 停止应用 | `sudo docker compose down` |
| 重启应用 | `sudo docker compose restart` |
| 查看日志 | `sudo docker compose logs -f` |
| 更新应用 | `sudo docker compose pull && sudo docker compose up -d` |
| 重启 Nginx | `sudo systemctl restart nginx` |
| 查看 Nginx 日志 | `sudo tail -f /var/log/nginx/madf.access.log` |

---

## 10. 安全建议

1. **修改 SSH 端口**：编辑 `/etc/ssh/sshd_config`，修改默认端口
2. **禁用 root 登录**：创建普通用户，禁用 root 直接 SSH 登录
3. **定期备份**：定期备份 `/opt/madf` 目录和数据库
4. **监控资源**：使用 `htop` 或腾讯云监控查看服务器资源使用情况

---

如有任何问题，请随时联系！
