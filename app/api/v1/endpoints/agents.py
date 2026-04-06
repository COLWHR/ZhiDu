from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import List, Optional
from pydantic import BaseModel
import json
import logging
from utils import get_chat_completion
from app.api.deps import get_current_user

logger = logging.getLogger(__name__)

from app.db.session import get_db
from app.schemas import MessageResponse
from app.crud import create_message, get_forum_messages, save_chat_message, get_chat_history, clear_chat_history
from app.agent.agent import ParticipantAgent
from app.agent.memory import SharedMemory

router = APIRouter()

class AgentChatRequest(BaseModel):
    agent_name: str
    persona_json: dict
    context_messages: List[dict]
    theme: str = "AI对未来的影响"

class AgentChatResponse(BaseModel):
    content: str
    thought: Optional[dict] = None

@router.post("/chat", response_model=AgentChatResponse)
async def chat_with_agent(request: AgentChatRequest):
    """
    Directly invoke an agent to think and speak based on provided context.
    This is a stateless endpoint wrapper around the ParticipantAgent logic.
    """
    # 1. Reconstruct Agent
    try:
        agent = ParticipantAgent(
            name=request.agent_name, 
            persona=request.persona_json, 
            n_participants=3, # Default, doesn't affect single-turn much
            theme=request.theme
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to initialize agent: {str(e)}")

    # 2. Reconstruct Context
    # We need to convert the list of dicts into the string format expected by agent.think/speak
    # Or better, use SharedMemory to generate it if we want to reuse logic exactly.
    memory = SharedMemory(n_participants=3)
    for msg in request.context_messages:
        memory.add_message(msg.get("speaker", "Unknown"), msg.get("content", ""))
    
    context_str = memory.get_context_str()

    # 3. Think
    thought = agent.think(context_str)
    
    if not thought:
        raise HTTPException(status_code=500, detail="Agent failed to think")

    # 4. Speak
    # If agent decides to listen, we return empty content but include thought
    if thought.get("action") == "listen":
        return AgentChatResponse(content="", thought=thought)

    # If speaking
    response_stream = agent.speak(thought, context_str)
    
    full_content = ""
    if response_stream:
        for chunk in response_stream:
            if chunk.choices[0].delta.content:
                full_content += chunk.choices[0].delta.content
    
    return AgentChatResponse(content=full_content, thought=thought)


@router.post("/chat/stream")
async def chat_with_agent_stream(request: AgentChatRequest):
    """
    简化版单聊接口，直接与智能体对话，流式响应，速度更快
    支持多模态输入：如果消息中包含图片URL，自动使用视觉大模型
    """
    persona = request.persona_json
    system_prompt = persona.get('system_prompt', '你是一个专业的智能助手。')
    
    # 构造消息历史，检测是否包含图片
    messages = [{"role": "system", "content": system_prompt}]
    use_vision = False
    
    for msg in request.context_messages:
        role = "user" if msg.get("speaker") == "用户" else "assistant"
        content = msg.get("content", "")
        
        # 检测是否包含图片（格式：![image](url) 或 <img src="url">）
        has_image = "![image]" in content or "<img src=" in content
        
        if has_image and role == "user":
            use_vision = True
            # 提取图片URL，构造多模态消息格式
            # 支持火山引擎多模态格式：[{"type":"text","text":"..."}, {"type":"image_url","image_url":{"url":"..."}}]
            content_parts = []
            
            # 提取文本和图片
            import re
            # 先处理图片标签
            img_pattern = r'!\[image\]\((.*?)\)|<img[^>]+src=["\'](.*?)["\']'
            matches = list(re.finditer(img_pattern, content))
            
            last_idx = 0
            for match in matches:
                if match.start() > last_idx:
                    text_part = content[last_idx:match.start()].strip()
                    if text_part:
                        content_parts.append({"type": "text", "text": text_part})
                
                img_url = match.group(1) or match.group(2)
                content_parts.append({"type": "image_url", "image_url": {"url": img_url}})
                last_idx = match.end()
            
            if last_idx < len(content):
                text_part = content[last_idx:].strip()
                if text_part:
                    content_parts.append({"type": "text", "text": text_part})
            
            messages.append({
                "role": role,
                "content": content_parts
            })
        else:
            messages.append({
                "role": role,
                "content": content
            })
    
    async def generate():
        try:
            stream = get_chat_completion(messages, stream=True, use_vision=use_vision)
            for chunk in stream:
                if use_vision:
                    # 火山引擎返回格式
                    if "choices" in chunk and len(chunk["choices"]) > 0:
                        delta = chunk["choices"][0].get("delta", {})
                        if "content" in delta and delta["content"]:
                            content = delta["content"]
                            yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"
                else:
                    # 智谱AI返回格式
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/chat/history/{persona_id}")
async def get_user_chat_history(persona_id: int, db = Depends(get_db), current_user = Depends(get_current_user)):
    """获取用户与指定智能体的聊天历史"""
    history = get_chat_history(db, current_user.id, persona_id)
    return [
        {
            "role": msg.role,
            "content": msg.content,
            "timestamp": msg.created_at.timestamp() * 1000
        } for msg in history
    ]


@router.delete("/chat/history/{persona_id}")
async def clear_user_chat_history(persona_id: int, db = Depends(get_db), current_user = Depends(get_current_user)):
    """清空用户与指定智能体的聊天历史"""
    success = clear_chat_history(db, current_user.id, persona_id)
    return {"success": success}


class ChatMessageCreate(BaseModel):
    persona_id: int
    role: str
    content: str


@router.post("/chat/message")
async def save_chat_message_endpoint(
    request: ChatMessageCreate, 
    db = Depends(get_db), 
    current_user = Depends(get_current_user)
):
    """保存单聊消息"""
    msg = save_chat_message(
        db, 
        user_id=current_user.id, 
        persona_id=request.persona_id, 
        role=request.role, 
        content=request.content
    )
    return {"success": msg is not None, "id": msg.id if msg else None}
