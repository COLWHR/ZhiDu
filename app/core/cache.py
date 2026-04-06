import json
import logging
from typing import Any, Optional, List
from datetime import datetime, timedelta
from app.core.config import redis_client

logger = logging.getLogger(__name__)

# 内存缓存作为Redis降级方案
memory_cache = {}
MEMORY_CACHE_EXPIRE = 300  # 内存缓存默认过期时间5分钟

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class RedisService:
    """Redis 缓存与缓冲服务类，支持内存缓存降级"""

    @staticmethod
    def set_cache(key: str, value: Any, expire: int = 3600):
        """通用缓存写入，优先写Redis，失败则写内存缓存"""
        try:
            if redis_client:
                redis_client.set(key, json.dumps(value, cls=DateTimeEncoder), ex=expire)
                return True
            
            # Redis不可用时使用内存缓存
            memory_cache[key] = {
                "data": value,
                "expire_at": datetime.now() + timedelta(seconds=min(expire, MEMORY_CACHE_EXPIRE))
            }
            # 定期清理过期内存缓存
            RedisService._cleanup_memory_cache()
            return True
        except Exception as e:
            logger.error(f"缓存设置失败: {e}")
            return False

    @staticmethod
    def get_cache(key: str) -> Optional[Any]:
        """通用缓存读取，优先读Redis，失败则读内存缓存"""
        try:
            if redis_client:
                data = redis_client.get(key)
                return json.loads(data) if data else None
            
            # 从内存缓存读取
            cache_item = memory_cache.get(key)
            if cache_item and datetime.now() < cache_item["expire_at"]:
                return cache_item["data"]
            
            # 过期则删除
            if key in memory_cache:
                del memory_cache[key]
            return None
        except Exception as e:
            logger.error(f"缓存读取失败: {e}")
            return None

    @staticmethod
    def delete_cache(key: str) -> bool:
        """删除单个缓存"""
        try:
            if redis_client:
                redis_client.delete(key)
            
            # 同步删除内存缓存
            if key in memory_cache:
                del memory_cache[key]
            return True
        except Exception as e:
            logger.error(f"缓存删除失败: {e}")
            return False

    @staticmethod
    def delete_keys_pattern(pattern: str) -> int:
        """按模式批量删除缓存"""
        deleted_count = 0
        try:
            if redis_client:
                # Use scan_iter for robust cursor handling
                keys = list(redis_client.scan_iter(match=pattern, count=100))
                if keys:
                    logger.info(f"Deleting {len(keys)} Redis keys matching pattern '{pattern}'")
                    deleted_count = redis_client.delete(*keys)
            
            # 同步删除内存缓存中匹配的key
            keys_to_delete = [k for k in memory_cache.keys() if pattern.replace('*', '') in k]
            for k in keys_to_delete:
                del memory_cache[k]
                deleted_count += 1
            
            return deleted_count
        except Exception as e:
            logger.error(f"模式删除缓存失败: {e}")
            return 0

    @staticmethod
    def push_message(queue: str, message: Any):
        """消息缓冲：将数据推入队列尾部 (用于日志或消息缓冲)"""
        if not redis_client: return False
        try:
            redis_client.rpush(queue, json.dumps(message, cls=DateTimeEncoder))
            return True
        except Exception as e:
            logger.error(f"Redis 消息缓冲推送失败: {e}")
            return False

    @staticmethod
    def pop_messages(queue: str, count: int = 10) -> List[Any]:
        """批量获取并移除缓冲的消息 (用于批量写入数据库)"""
        if not redis_client: return []
        messages = []
        try:
            # 使用pipeline批量弹出，减少网络往返
            with redis_client.pipeline() as pipe:
                for _ in range(count):
                    pipe.lpop(queue)
                results = pipe.execute()
            
            for msg in results:
                if msg:
                    messages.append(json.loads(msg))
                else:
                    break
            
            return messages
        except Exception as e:
            logger.error(f"Redis 消息弹出失败: {e}")
            return []
        
    @staticmethod
    def _cleanup_memory_cache():
        """清理过期的内存缓存，避免内存泄漏"""
        now = datetime.now()
        expired_keys = [k for k, v in memory_cache.items() if now >= v["expire_at"]]
        for k in expired_keys:
            del memory_cache[k]

cache_service = RedisService()
