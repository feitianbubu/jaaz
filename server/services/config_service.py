import copy
import os
import traceback
import aiofiles
import toml
from typing import Dict, TypedDict, Literal, Optional
from utils.jwt_utils import JWTUtils

# 定义配置文件的类型结构


class ModelConfig(TypedDict, total=False):
    type: Literal["text", "image", "video"]
    is_custom: Optional[bool]
    is_disabled: Optional[bool]


class ProviderConfig(TypedDict, total=False):
    url: str
    api_key: str
    max_tokens: int
    models: Dict[str, ModelConfig]
    is_custom: Optional[bool]


AppConfig = Dict[str, ProviderConfig]


DEFAULT_PROVIDERS_CONFIG: AppConfig = {
    'jaaz': {
        'models': {
            # text models
            # 'gpt-4o': {'type': 'text'},
            # 'gpt-4o-mini': {'type': 'text'},
            # 'deepseek/deepseek-chat-v3-0324': {'type': 'text'},
            # 'anthropic/claude-sonnet-4': {'type': 'text'},
            # 'anthropic/claude-3.7-sonnet': {'type': 'text'},
            'kimi-k2-0905-preview': {'type': 'text'},
            # video models
            'jimeng_i2v_first_v30_1080': {'type': 'video', 'display_name': 'Jimeng3.0', 'description': 'Generate high-quality videos using jimeng_i2v_first_v30_1080 model. Supports image-to-video generation with advanced controls.'},
            # 'kling-v1': {'type': 'video', 'display_name': 'Kling V1', 'description': 'Generate high-quality videos using Kling V1 model. Supports image-to-video generation with advanced controls.'},
            # 'viduq1': {'type': 'video', 'display_name': 'viduq1', 'description': 'Generate high-quality videos using viduq1model. Supports image-to-video generation with advanced controls.'},
        },
        'url': os.getenv('BASE_API_URL', 'https://jaaz.app').rstrip('/') + '/v1/',
        'api_key': '',
        'max_tokens': 8192,
    },
    'comfyui': {
        'models': {},
        'url': 'http://127.0.0.1:8188',
        'api_key': '',
    },
    'ollama': {
        'models': {},
        'url': 'http://localhost:11434',
        'api_key': '',
        'max_tokens': 8192,
    },
    'openai': {
        'models': {
            # 'gpt-4o': {'type': 'text'},
            # 'gpt-4o-mini': {'type': 'text'},
        },
        'url': 'https://api.openai.com/v1/',
        'api_key': '',
        'max_tokens': 8192,
    },

}

SERVER_DIR = os.path.dirname(os.path.dirname(__file__))
USER_DATA_DIR = os.getenv(
    "USER_DATA_DIR",
    os.path.join(SERVER_DIR, "user_data"),
)
FILES_DIR = os.path.join(USER_DATA_DIR, "files")


IMAGE_FORMATS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",  # 基础格式
    ".bmp",
    ".tiff",
    ".tif",  # 其他常见格式
    ".webp",
)
VIDEO_FORMATS = (
    ".mp4",
    ".avi",
    ".mkv",
    ".mov",
    ".wmv",
    ".flv",
)


class ConfigService:
    def __init__(self):
        self.app_config: AppConfig = copy.deepcopy(DEFAULT_PROVIDERS_CONFIG)
        self.config_file = os.getenv(
            "CONFIG_PATH", os.path.join(USER_DATA_DIR, "config.toml")
        )
        self.initialized = False

    def _get_jaaz_url(self) -> str:
        """Get the correct jaaz URL"""
        return os.getenv('BASE_API_URL', 'https://newapi.clinx.work').rstrip('/') + '/v1/'

    async def initialize(self) -> None:
        try:
            # Ensure the user_data directory exists
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)

            # Check if config file exists
            if not self.exists_config():
                print(
                    f"Config file not found at {self.config_file}, creating default configuration")
                # Create default config file
                with open(self.config_file, "w") as f:
                    toml.dump(self.app_config, f)
                print(f"Default config file created at {self.config_file}")
                self.initialized = True
                return

            async with aiofiles.open(self.config_file, "r") as f:
                content = await f.read()
                config: AppConfig = toml.loads(content)
            for provider, provider_config in config.items():
                if provider not in DEFAULT_PROVIDERS_CONFIG:
                    provider_config['is_custom'] = True
                self.app_config[provider] = provider_config
                # image/video models are hardcoded in the default provider config
                provider_models = DEFAULT_PROVIDERS_CONFIG.get(
                    provider, {}).get('models', {})
                for model_name, model_config in provider_config.get('models', {}).items():
                    # Only text model can be self added
                    if model_config.get('type') == 'text' and model_name not in provider_models:
                        provider_models[model_name] = model_config
                        provider_models[model_name]['is_custom'] = True
                self.app_config[provider]['models'] = provider_models

            # 确保 jaaz URL 始终正确
            if 'jaaz' in self.app_config:
                self.app_config['jaaz']['url'] = self._get_jaaz_url()
        except Exception as e:
            print(f"Error loading config: {e}")
            traceback.print_exc()
        finally:
            self.initialized = True

    def get_config(self) -> AppConfig:
        if 'jaaz' in self.app_config:
            self.app_config['jaaz']['url'] = self._get_jaaz_url()
        return self.app_config

    async def update_config(self, data: AppConfig) -> Dict[str, str]:
        try:
            if 'jaaz' in data:
                data['jaaz']['url'] = self._get_jaaz_url()

            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, "w") as f:
                toml.dump(data, f)
            self.app_config = data

            return {
                "status": "success",
                "message": "Configuration updated successfully",
            }
        except Exception as e:
            traceback.print_exc()
            return {"status": "error", "message": str(e)}

    def exists_config(self) -> bool:
        return os.path.exists(self.config_file)

    def get_provider_config_for_token(self, provider: str, token: str) -> Dict:
        """
        为特定用户获取provider配置，插入用户token到配置中
        """
        # 获取基础配置
        config = self.app_config.get(provider, {}).copy()
        
        # 如果有token，返回配置且api_key为用户token
        if token and token.strip():
            config['api_key'] = token
            print(f"🔑 Using user-specific API key for {provider} provider")
        
        return config
    
    def set_user_api_key_from_token(self, provider: str, token: str) -> Dict[str, str]:
        """
        通过JWT token设置用户级别的provider api_key
        这是一个开销销的方法，不进行配置结构性变化，仅在内存中临时应用
        """
        try:
            # 解析token获取用户信息
            user_id = JWTUtils.extract_user_id(token)
            username = JWTUtils.extract_username(token)
            
            if not user_id:
                return {"status": "error", "message": "Invalid token: cannot extract user_id"}
            
            # 这里应该实现基于用户的配置存储
            # 但采用最简单方案：在当前配置基础上直接更新用户的配置
            if provider in self.app_config:
                # 暂时在全局配置中设置用户token（临时解决方案）
                self.app_config[provider]['api_key'] = token
                return {
                    "status": "success",
                    "message": f"Updated {provider} API key for user {user_id}",
                    "user_id": user_id,
                    "username": username
                }
            else:
                return {"status": "error", "message": f"Provider {provider} not found"}
                
        except Exception as e:
            traceback.print_exc()
            return {"status": "error", "message": f"Failed to set API key: {str(e)}"}
    
    def clear_user_session(self, user_id: str) -> None:
        """
        清除用户会话配置（恢复全局配置）
        """
        try:
            # 恢复为全局默认配置
            if 'jaaz' in self.app_config:
                # 如果原配置有保存，恢复原有的全局api_key  
                self.app_config['jaaz']['api_key'] = ''  # 清空用户配置，使用全局配置
            print(f"🧹 Cleared user session config for {user_id}")
        except Exception as e:
            print(f"Error clearing user session: {e}")



config_service = ConfigService()
