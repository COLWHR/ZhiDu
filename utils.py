import os
import json
import time
import re
import base64
import requests
from zhipuai import ZhipuAI, APIRequestFailedError, APITimeoutError
try:
    from zhipuai import APIError
except ImportError:
    # Handle older versions or different structure where APIError might be named differently or not exported
    # But usually it is there. Let's check if it's ZhipuAIError or similar.
    # Actually, let's just use Exception as fallback if not found.
    class APIError(Exception): pass
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


def _configured_api_key() -> str:
    return (
        settings.API_KEY
        or os.environ.get("API_KEY")
        or os.environ.get("ZHIPUAI_API_KEY")
        or ""
    ).strip()


def _looks_like_placeholder_api_key(key: str) -> bool:
    normalized = key.strip().lower()
    if not normalized:
        return False

    placeholder_tokens = (
        "replace_with_your_zhipu_api_key",
        "your_zhipu_api_key",
        "your_api_key",
        "your key",
        "change_me",
        "placeholder",
        "example_key",
        "dummy_key",
    )
    return (
        normalized.startswith("replace_with")
        or normalized.startswith("your_")
        or normalized.startswith("xxx")
        or any(token in normalized for token in placeholder_tokens)
    )


def _build_llm_client() -> ZhipuAI:
    api_key = _configured_api_key()
    if not api_key:
        raise LLMServiceError(
            kind="auth",
            message="未配置 API_KEY，请在 .env 或环境变量中填入真实的智谱 API Key。",
        )

    if _looks_like_placeholder_api_key(api_key):
        raise LLMServiceError(
            kind="auth",
            message="API_KEY 仍是示例占位符，请替换为真实密钥后再试。",
        )

    return ZhipuAI(
        api_key=api_key,
        base_url=settings.final_base_url,
    )


class LLMServiceError(RuntimeError):
    """Structured error for upstream LLM failures."""

    def __init__(self, kind: str, message: str, *, status_code: int | None = None, details: str | None = None):
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.status_code = status_code
        self.details = details

    @classmethod
    def from_exception(cls, exc: Exception, *, timeout: int | None = None) -> "LLMServiceError":
        raw = str(exc).strip() or exc.__class__.__name__
        lowered = raw.lower()

        def has(*tokens: str) -> bool:
            return any(token in raw or token in lowered for token in tokens)

        if has("401", "unauthorized", "身份验证失败", "api key", "apikey", "invalid api key", "invalid api_key"):
            return cls(
                kind="auth",
                message="上游模型鉴权失败（401 Unauthorized / 身份验证失败）",
                status_code=401,
                details=raw,
            )

        if has("403", "forbidden", "无权限", "permission denied"):
            return cls(
                kind="permission",
                message="上游模型权限不足（403 Forbidden）",
                status_code=403,
                details=raw,
            )

        if has("404", "not found", "模型不存在", "资源未找到"):
            return cls(
                kind="not_found",
                message="上游模型或接口地址未找到（404 Not Found）",
                status_code=404,
                details=raw,
            )

        if has("429", "rate limit", "too many requests", "限流", "请求过于频繁"):
            return cls(
                kind="rate_limit",
                message="上游模型触发限流（429 Too Many Requests）",
                status_code=429,
                details=raw,
            )

        if has("timeout", "timed out", "超时"):
            timeout_suffix = f"（{timeout}s）" if timeout else ""
            return cls(
                kind="timeout",
                message=f"上游模型请求超时{timeout_suffix}",
                details=raw,
            )

        if has("connection", "connect", "network", "unreachable", "refused", "dns"):
            return cls(
                kind="network",
                message="无法连接到上游模型服务，请检查网络或 BASE_URL",
                details=raw,
            )

        return cls(kind="upstream_error", message=f"上游模型调用失败：{raw}", details=raw)


# 全局变量用于跟踪API调用频率和速率限制状态
api_call_history = []
rate_limit_backoff = 0


def get_chat_completion(messages, stream=False, json_mode=False, max_retries=3, timeout=30, callback=None, raise_error=False, use_vision=False):
    """
    Wrapper for ZhipuAI chat completion with retry logic and timeout.
    
    Args:
        callback: Optional async function(error_msg: str) to report errors to system log
        raise_error: If True, raise the last exception instead of returning None when all retries fail.
        use_vision: If True, use volcanic engine visual model for multimodal input
    """
    global api_call_history
    global rate_limit_backoff
    
    # 清理过期的API调用记录（1分钟内）
    current_time = time.time()
    api_call_history = [t for t in api_call_history if current_time - t < 60]
    
    # 检查是否需要速率限制
    if rate_limit_backoff > current_time:
        wait_time = rate_limit_backoff - current_time
        logger.warning(f"Rate limit detected, waiting {wait_time:.2f} seconds...")
        time.sleep(wait_time)
    
    attempt = 0
    last_error = None
    
    # 如果是多模态请求且配置了火山引擎API，使用火山引擎视觉模型
    if use_vision and settings.VOLC_API_KEY:
        while attempt < max_retries:
            try:
                headers = {
                    "Authorization": f"Bearer {settings.VOLC_API_KEY}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "model": settings.VOLC_VISION_MODEL,
                    "messages": messages,
                    "stream": stream,
                    "temperature": 0.8,
                    "max_tokens": 4096,
                    "top_p": 0.7
                }
                
                response = requests.post(
                    f"{settings.VOLC_BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=timeout,
                    stream=stream
                )
                response.raise_for_status()
                
                if stream:
                    # 返回流式迭代器
                    def stream_generator():
                        for line in response.iter_lines():
                            if line:
                                line = line.decode('utf-8')
                                if line.startswith('data: '):
                                    data = line[6:]
                                    if data == '[DONE]':
                                        break
                                    try:
                                        yield json.loads(data)
                                    except:
                                        continue
                    return stream_generator()
                else:
                    return response.json()
                    
            except requests.exceptions.RequestException as e:
                error_msg = f"Volc API Request Failed (Attempt {attempt+1}/{max_retries}): {e}"
                logger.warning(error_msg)
                last_error = e
                
            attempt += 1
            if attempt < max_retries:
                time.sleep(1 + attempt)

        if last_error:
            logger.warning(
                "Vision API failed after %s attempts; falling back to text model: %s",
                max_retries,
                last_error,
            )
    
    # 普通文本请求或火山引擎不可用，使用智谱AI
    client = _build_llm_client()
    while attempt < max_retries:
        try:
            # 记录API调用时间
            api_call_history.append(time.time())
            
            # 检查调用频率（每分钟最多60次）
            if len(api_call_history) > 60:
                oldest_call = api_call_history[0]
                wait_time = 60 - (current_time - oldest_call)
                if wait_time > 0:
                    logger.warning(f"API call frequency too high, waiting {wait_time:.2f} seconds...")
                    time.sleep(wait_time)
            
            if stream:
                return client.chat.completions.create(
                    model=settings.MODEL_NAME,
                    messages=messages,
                    stream=True,
                    temperature=0.8,
                    max_tokens=4096,
                    top_p=0.7,
                    timeout=timeout
                )
            
            response = client.chat.completions.create(
                model=settings.MODEL_NAME,
                messages=messages,
                stream=False,
                temperature=0.8,
                max_tokens=4096,
                top_p=0.7,
                timeout=timeout
            )
            
            # 成功调用后重置速率限制状态
            rate_limit_backoff = 0
            return response
            
        except APIRequestFailedError as e:
            # 429 Rate Limit or 500 Server Error
            error_msg = f"API Request Failed (Attempt {attempt+1}/{max_retries}): {e}"
            logger.warning(error_msg)
            
            # 处理速率限制错误
            if "429" in str(e):
                # 计算退避时间（指数退避）
                backoff_time = (2 ** attempt) * 5  # 5s, 10s, 20s...
                logger.warning(f"Rate limit exceeded, backing off for {backoff_time} seconds...")
                time.sleep(backoff_time)
                # 设置全局退避时间
                rate_limit_backoff = time.time() + backoff_time
            
            if callback:
                # We can't await here easily as this is sync function, 
                # but caller usually wraps this in to_thread.
                # So we can't call async callback directly.
                # Just log for now.
                pass
            last_error = e
            
        except APITimeoutError as e:
            error_msg = f"API Timeout ({timeout}s) (Attempt {attempt+1}/{max_retries})"
            logger.warning(error_msg)
            last_error = e
            
        except APIError as e:
            error_msg = f"API Error (Attempt {attempt+1}/{max_retries}): {e}"
            logger.warning(error_msg)
            last_error = e
            
        except Exception as e:
            error_msg = f"Unknown Error (Attempt {attempt+1}/{max_retries}): {e}"
            logger.error(error_msg)
            last_error = e
            
        attempt += 1
        if attempt < max_retries:
            # 指数退避策略
            backoff_time = (2 ** attempt) * 2  # 2s, 4s, 8s...
            logger.info(f"Retrying in {backoff_time} seconds...")
            time.sleep(backoff_time)
            
    logger.error(f"Chat completion failed after {max_retries} attempts. Last error: {last_error}")
    
    if raise_error and last_error:
        raise LLMServiceError.from_exception(last_error, timeout=timeout)
    if raise_error:
        raise LLMServiceError(
            kind="empty_response",
            message="上游模型未返回有效响应",
        )
        
    return None

def parse_json_from_response(content):
    """
    Attempts to parse JSON from a string, handling code blocks if present.
    Also handles common LLM JSON errors like unescaped quotes.
    """
    try:
        content = content.strip()
        
        # 1. Try to extract JSON from markdown code blocks
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
        if json_match:
            content = json_match.group(1)
        else:
            # 2. If no code blocks, try to find the first outer-most JSON object or array
            # Find the first '{' or '['
            start_idx = -1
            end_idx = -1
            stack = []
            
            for i, char in enumerate(content):
                if char in '{[':
                    if start_idx == -1:
                        start_idx = i
                    stack.append(char)
                elif char in '}]':
                    if stack:
                        last = stack[-1]
                        if (last == '{' and char == '}') or (last == '[' and char == ']'):
                            stack.pop()
                            if not stack:
                                end_idx = i + 1
                                break
            
            if start_idx != -1 and end_idx != -1:
                content = content[start_idx:end_idx]

        return json.loads(content)
    except json.JSONDecodeError as e:
        print(f"Standard JSON parse failed: {e}. Attempting cleanup...")
        
        try:
            import dirtyjson
            return dirtyjson.loads(content)
        except Exception:
            pass

        def escape_unescaped_quotes(raw: str) -> str:
            result = []
            in_string = False
            i = 0
            while i < len(raw):
                char = raw[i]
                if char == "\\" and in_string and i + 1 < len(raw):
                    result.append(char)
                    result.append(raw[i + 1])
                    i += 2
                    continue
                if char == '"':
                    if not in_string:
                        in_string = True
                        result.append(char)
                    else:
                        j = i + 1
                        while j < len(raw) and raw[j].isspace():
                            j += 1
                        if j == len(raw) or raw[j] in {',', '}', ']', ':'}:
                            in_string = False
                            result.append(char)
                        else:
                            result.append('\\"')
                    i += 1
                    continue
                result.append(char)
                i += 1
            return ''.join(result)

        # Cleanup: remove trailing commas, comments
        try:
            # Remove single-line comments // ...
            content = re.sub(r'//.*', '', content)
            # Remove trailing commas before } or ]
            content = re.sub(r',(\s*[}\]])', r'\1', content)

            try:
                return json.loads(content)
            except json.JSONDecodeError:
                repaired = escape_unescaped_quotes(content)
                return json.loads(repaired)
        except Exception:
            pass
            
        print(f"Failed to parse JSON content: {content[:200]}...")
        return None
