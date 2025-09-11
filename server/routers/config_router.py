from fastapi import APIRouter, Request
from services.config_service import config_service
# from tools.video_models_dynamic import register_video_models  # Disabled video models
from services.tool_service import tool_service

router = APIRouter(prefix="/api/config")


@router.get("/exists")
async def config_exists():
    return {"exists": config_service.exists_config()}


@router.get("")
async def get_config():
    return config_service.app_config


@router.post("")
async def update_config(request: Request):
    data = await request.json()
    res = await config_service.update_config(data)

    # 每次更新配置后，重新初始化工具
    await tool_service.initialize()
    return res


@router.post("/jaaz-api-key")
async def set_jaaz_api_key(request: Request):
    """设置jaaz provider的api_key，从JWT token中解析user_id"""
    data = await request.json()
    token = data.get('token')
    
    if not token:
        return {"status": "error", "message": "Token is required"}
    
    result = config_service.set_user_api_key_from_token('jaaz', token)
    return result


@router.delete("/user-session")
async def clear_user_session(request: Request):
    """清除用户会话配置"""
    data = await request.json()
    token = data.get('token')
    
    if not token:
        return {"status": "error", "message": "Token is required"}
    
    from utils.jwt_utils import JWTUtils
    user_id = JWTUtils.extract_user_id(token)
    
    if not user_id:
        return {"status": "error", "message": "Invalid token: cannot extract user_id"}
    
    config_service.clear_user_session(user_id)
    return {"status": "success", "message": f"Session cleared for user {user_id}"}
