import os
from fastapi import APIRouter, Request
import requests
from services.config_service import config_service
from services.db_service import db_service

#services
from services.files_service import download_file
from services.websocket_service import broadcast_init_done

router = APIRouter(prefix="/api")

# @router.get("/workspace_list")
# async def workspace_list():
#     return [{"name": entry.name, "is_dir": entry.is_dir(), "path": str(entry)} for entry in Path(WORKSPACE_ROOT).iterdir()]

async def initialize():
    # await initialize_mcp()
    await broadcast_init_done()

@router.get("/workspace_download")
async def workspace_download(path: str):
    return download_file(path)

def get_ollama_model_list():
    base_url = config_service.get_config().get('ollama', {}).get(
        'url', os.getenv('OLLAMA_HOST', 'http://localhost:11434'))
    try:
        response = requests.get(f'{base_url}/api/tags', timeout=5)
        response.raise_for_status()
        data = response.json()
        return [model['name'] for model in data.get('models', [])]
    except requests.RequestException as e:
        print(f"Error querying Ollama: {e}")
        return []


async def list_models_clinx(token: str):
    if not token:
        return []
    try:
        response = requests.get(
            "https://newapi.clinx.work/providers/modelsList",
            headers={"Authorization": token},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        # 结构转换
        models = data.get("data", {}).get("list", [])
        res = []
        for m in models:
            model_type = m.get("model_type", "text")
            if model_type == "llm":
                model_type = "text"
            res.append({
                "provider": "clinx",
                "url": "https://newapi.clinx.work/v1",
                "model": m.get("model_name", ""),
                "type": model_type,
                "priority": m.get("priority", 0)
            })
        return res
    except Exception as e:
        print(f"Error fetching models from clinx: {e}")
        return []


@router.get("/list_models")
async def get_models(request: Request):
    token = request.headers.get("authorization")
    clinx_models = await list_models_clinx(token)

    config = config_service.get_config()
    comfyui_models = []
    if 'comfyui' in config:
        models = config['comfyui'].get('models', {})
        for model_name in models:
            model = models[model_name]
            comfyui_models.append({
                'provider': 'comfyui',
                'model': model_name,
                'url': config['comfyui'].get('url', ''),
                'type': model.get('type', 'text')
            })
    
    return clinx_models + comfyui_models


@router.get("/list_chat_sessions")
async def list_chat_sessions():
    return await db_service.list_sessions()


@router.get("/chat_session/{session_id}")
async def get_chat_session(session_id: str):
    return await db_service.get_chat_history(session_id)
