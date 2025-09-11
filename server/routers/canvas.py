from fastapi import APIRouter, Request
#from routers.agent import chat
from services.chat_service import handle_chat
from services.db_service import db_service
import asyncio
import json

router = APIRouter(prefix="/api/canvas")

@router.get("/list")
async def list_canvases():
    return await db_service.list_canvases()

@router.post("/create")
async def create_canvas(request: Request):
    data = await request.json()
    
    # Extract token from Authorization header - 与chat_router保持一致
    token = None
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
    
    # Also check for authorization in lowercase
    if not token:
        auth_header_lower = request.headers.get('authorization', '')
        if auth_header_lower.startswith('Bearer '):
            token = auth_header_lower[7:]
    
    # Add token to data if found
    if token:
        data['token'] = token
    
    id = data.get('canvas_id')
    name = data.get('name')

    asyncio.create_task(handle_chat(data))  
    await db_service.create_canvas(id, name)
    return {"id": id }

@router.get("/{id}")
async def get_canvas(id: str):
    return await db_service.get_canvas_data(id)

def extract_token_from_request(request: Request) -> str | None:
    """统一提取token函数"""
    token = None
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
    
    if not token:
        auth_header_lower = request.headers.get('authorization', '')
        if auth_header_lower.startswith('Bearer '):
            token = auth_header_lower[7:]
    
    return token

@router.post("/{id}/save")
async def save_canvas(id: str, request: Request):
    payload = await request.json()
    data_str = json.dumps(payload['data'])
    await db_service.save_canvas_data(id, data_str, payload['thumbnail'])
    return {"id": id }

@router.post("/{id}/rename")
async def rename_canvas(id: str, request: Request):
    data = await request.json()
    name = data.get('name')
    await db_service.rename_canvas(id, name)
    return {"id": id }

@router.delete("/{id}/delete")
async def delete_canvas(id: str):
    await db_service.delete_canvas(id)
    return {"id": id }