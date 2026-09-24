from fastapi import APIRouter, Depends, HTTPException
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Conversation, ConversationMessage, User

router = APIRouter(prefix="/conversations", tags=["conversations"])


class ConversationCreate(BaseModel):
    title: str = Field(default="新的学习对话", min_length=1, max_length=120)


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=10000)


def conversation_data(item: Conversation) -> dict:
    return {"id": item.id, "title": item.title, "created_at": item.created_at.isoformat(), "updated_at": item.updated_at.isoformat()}


async def owned(conversation_id: str, user_id: str, db: AsyncSession) -> Conversation:
    item = await db.scalar(select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user_id))
    if not item:
        raise HTTPException(status_code=404, detail="会话不存在")
    return item


@router.get("")
async def list_conversations(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await db.scalars(select(Conversation).where(Conversation.user_id == user.id).order_by(Conversation.updated_at.desc()).limit(50))
    return {"data": [conversation_data(item) for item in rows]}


@router.post("")
async def create_conversation(body: ConversationCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    item = Conversation(user_id=user.id, title=body.title.strip())
    db.add(item); await db.commit(); await db.refresh(item)
    return {"data": conversation_data(item)}


@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    item = await owned(conversation_id, user.id, db)
    messages = await db.scalars(select(ConversationMessage).where(ConversationMessage.conversation_id == item.id).order_by(ConversationMessage.created_at))
    return {"data": {**conversation_data(item), "messages": [{"id": msg.id, "role": msg.role, "content": msg.content, "created_at": msg.created_at.isoformat()} for msg in messages]}}


@router.post("/{conversation_id}/messages")
async def send_message(conversation_id: str, body: MessageCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    conversation = await owned(conversation_id, user.id, db)
    user_message = ConversationMessage(conversation_id=conversation.id, role="user", content=body.content.strip())
    db.add(user_message); await db.flush()
    response_text = "消息已记录。配置 DashScope API Key 后，向导会在这里继续回答。"
    provider_status = "unconfigured"
    if settings.dashscope_api_key:
        history = await db.scalars(select(ConversationMessage).where(ConversationMessage.conversation_id == conversation.id).order_by(ConversationMessage.created_at))
        client = AsyncOpenAI(api_key=settings.dashscope_api_key, base_url=settings.llm_base_url)
        try:
            response = await client.chat.completions.create(model=settings.llm_model, messages=[{"role": msg.role, "content": msg.content} for msg in history])
            response_text = response.choices[0].message.content or "我暂时没有生成回复。"
            provider_status = "completed"
        except Exception:
            response_text = "模型暂时不可用，消息已保存，你可以稍后重试。"
            provider_status = "unavailable"
        finally:
            await client.close()
    assistant = ConversationMessage(conversation_id=conversation.id, role="assistant", content=response_text)
    db.add(assistant); await db.commit(); await db.refresh(assistant)
    return {"data": {"message": {"id": assistant.id, "role": assistant.role, "content": assistant.content}, "provider_status": provider_status}}
