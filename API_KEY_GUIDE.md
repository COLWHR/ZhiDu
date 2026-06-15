# 获取模型 API Key 的方法

本文以智谱开放平台为例，说明如何获取可用的模型服务密钥。

## 1. 注册和登录

1. 打开智谱开放平台：<https://open.bigmodel.cn/>
2. 注册账号或直接登录已有账号

## 2. 进入控制台

1. 登录后进入控制台
2. 找到 API Key 或密钥管理入口

## 3. 创建密钥

1. 点击创建 API Key
2. 复制生成的密钥并妥善保存
3. 不要把密钥提交到仓库或公开分享

## 4. 配置到项目中

在项目根目录创建 `.env`，把密钥写入 `API_KEY`：

```ini
API_KEY=your_api_key_here
MODEL_NAME=glm-4.5
BASE_URL=https://open.bigmodel.cn/api/paas/v4/
SECRET_KEY=your_secret_key
```

说明：

- `API_KEY` 必填
- `MODEL_NAME` 默认使用 `glm-4.5`
- 如果你的账号已经开通对应能力，也可以改成 `glm-4.6`

## 5. 常见问题

- 如果接口返回 401，优先确认密钥是否复制正确
- 如果提示额度不足，检查账号余额或模型配额
- 如果服务报错，确认 `BASE_URL` 是否与平台要求一致

