# 获取智谱 AI API Key 详细步骤

## 步骤 1: 访问智谱 AI 开放平台

1. 打开浏览器，访问智谱 AI 开放平台：[https://open.bigmodel.cn/](https://open.bigmodel.cn/)

2. 点击页面右上角的「注册」按钮，创建一个新账号（如果已有账号则直接登录）。

## 步骤 2: 登录并进入控制台

1. 使用注册的账号登录智谱 AI 开放平台。

2. 登录后，点击页面右上角的「控制台」按钮，进入开发者控制台。

## 步骤 3: 获取 API Key

1. 在控制台页面，找到左侧导航栏中的「API 密钥」或类似选项。

2. 点击「创建 API 密钥」按钮，系统会生成一个新的 API Key。

3. 复制生成的 API Key，妥善保存。

## 步骤 4: 配置环境变量

1. 在项目根目录下，复制 `.env.example` 文件并重命名为 `.env`。

2. 编辑 `.env` 文件，将获取到的 API Key 填入 `API_KEY` 字段。

```ini
# LLM API Configuration
API_KEY=your_glm_api_key  # 替换为你的 API Key
MODEL_NAME=glm-4.6
BASE_URL=https://open.bigmodel.cn/api/paas/v4/

# Search API Configuration
SERPAPI_API_KEY=your_serpapi_key
DATABASE_URL=
```

## 注意事项

1. API Key 是敏感信息，请不要分享给他人。

2. 智谱 AI 可能会对 API 调用次数进行限制，请注意查看相关的使用条款。

3. 如果遇到 API 调用失败的情况，请检查 API Key 是否正确，以及是否有足够的配额。

获取 API Key 后，请通知我，我将继续指导您完成本地源码启动的后续步骤。