# LLM 路由与 `.env` 最小配置

这份文档描述当前后端的模型分层规则。它不绑定任何特定厂商，`MODEL_NAME` 可以替换成你实际可用的任意模型，只要对应 SDK 和 `BASE_URL` 能正常调用即可。

## 最小必填项

```env
API_KEY=your_api_key
MODEL_NAME=your_main_model
BASE_URL=https://your-llm-provider.example/v1
```

## 可选分层项

```env
FAST_MODEL_NAME=your_fast_model
REASONING_MODEL_NAME=your_reasoning_model
VISION_MODEL_NAME=your_vision_model
```

## 路由映射

| 路由名 | 作用 | 推荐模型层 |
| --- | --- | --- |
| `single_chat` | 单聊直接回复 | `MODEL_NAME` |
| `forum_think` | 论坛参与者是否发言的快速判断 | `FAST_MODEL_NAME` |
| `forum_speak` | 论坛参与者正式发言 | `MODEL_NAME` |
| `summary` | 轮次总结/压缩 | `FAST_MODEL_NAME` |
| `reasoning` | 高价值推理、收尾总结 | `REASONING_MODEL_NAME` |
| `vision` | 图片/多模态输入 | `VISION_MODEL_NAME` |
| `nvwa_count` | 女娲功能中的数量判断 | `FAST_MODEL_NAME` |
| `nvwa_generate` | 女娲功能中的 persona 生成 | `REASONING_MODEL_NAME` |

## 推荐配置原则

1. `FAST_MODEL_NAME` 选便宜、响应快的模型，用于分类、数量判断、摘要。
2. `MODEL_NAME` 选日常对话主力模型，用于大多数回复。
3. `REASONING_MODEL_NAME` 选更强的推理模型，只给复杂生成、最终总结、女娲 persona 生成这类高价值请求。
4. 如果你只配了 `MODEL_NAME`，系统会自动回退到同一个模型，不影响功能。

## 女娲功能

“女娲功能”指 persona 生成链路：

1. `get_persona_count(...)` 先判断数量，走 `nvwa_count`。
2. `generate_personas(...)` 和 `RealGodAgent` 的实际生成过程走 `nvwa_generate`。
3. 这意味着你可以给女娲功能单独配置更强的推理模型，而不会影响论坛和普通单聊的成本。

## 示例

```env
API_KEY=xxx
BASE_URL=https://open.bigmodel.cn/api/paas/v4/
MODEL_NAME=glm-4.5
FAST_MODEL_NAME=glm-4-flash
REASONING_MODEL_NAME=glm-4.5
VISION_MODEL_NAME=doubao-vision-pro-12k
```

这个例子只是说明写法，不限定必须用 GLM。
