# services/OpenAIAgents_service/jaaz_service.py

import io
import http.cookies

import asyncio
import aiohttp
import tempfile
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import json
import time
from io import BytesIO
from aiohttp import FormData
from utils.http_client import HttpClient
from services.config_service import config_service
from tools.utils.image_utils import process_input_image
from tools.utils.upload_utils import upload_image_from_file_path, upload_image_direct
from tools.video_generation.video_canvas_utils import (
    send_video_start_notification,
    process_video_result,
    send_video_completion_notification,
    send_video_error_notification
)
import openai
from services.openai_video_http_client import OpenAIVideoHttpClient


class JaazService:
    """Jaaz 云端 API 服务
    """

    def __init__(self, token: str = None):
        """初始化 Jaaz 服务

        Args:
            token: JWT token用于视频生成认证，如果提供则覆盖配置文件中的api_key
        """
        config = config_service.app_config.get('jaaz', {})
        self.api_url = str(config.get("url", "")).rstrip("/")
        # 优先使用传入的token，其次使用配置文件中的api_key
        self.api_token = token if token else str(config.get("api_key", ""))

        if not self.api_url:
            raise ValueError("Jaaz API URL is not configured")
        if not self.api_token:
            raise ValueError("Jaaz API token is not configured")

        # 确保 API 地址以 /api/v1 结尾
        # if not self.api_url.endswith('/api/v1'):
        #     self.api_url = f"{self.api_url}/api/v1"

        # 初始化 OpenAI 客户端
        self.openai_client = openai.OpenAI(
            api_key=self.api_token,
            base_url=self.api_url
        )

        # 初始化 HTTP 客户端（用于多个 input_reference）
        self.openai_http_client = OpenAIVideoHttpClient(
            api_key=self.api_token,
            base_url=self.api_url
        )

        print(f"✅ Jaaz service initialized with API URL: {self.api_url}")

    async def _download_image(self, url: str) -> str:
        async with HttpClient.create_aiohttp() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise ValueError(f"Failed to download image: {response.status}")

                suffix = Path(url).suffix or '.jpg'
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                    tmp_file.write(await response.read())
                    return tmp_file.name

    async def _create_openai_video_task(self, prompt: str, model: str, image_paths: List[str] = None, resolution: str = None, duration: int = None, aspect_ratio: str = None) -> str:
        """使用 OpenAI SDK 创建视频生成任务"""
        print(f"🎬 Creating OpenAI video task:")
        print(f"  model: {repr(model)}")
        print(f"  prompt: {repr(prompt[:100])}")
        print(f"  image_paths: {repr(image_paths)}")
        print(f"  resolution: {repr(resolution)}")
        print(f"  duration: {repr(duration)}")
        print(f"  aspect_ratio: {repr(aspect_ratio)}")

        # 如果有多个图片，使用 HTTP 客户端支持多个 input_reference
        if image_paths and len(image_paths) > 1:
            print(f"🚀 Detected {len(image_paths)} images, using HTTP client for multiple input_reference support")
            try:
                # 使用 HTTP 客户端支持多个 input_reference
                video_id = await self.openai_http_client.create_video_with_multiple_images(
                    prompt=prompt,
                    model=model or "sora-2",
                    image_paths=image_paths,
                    resolution=resolution,
                    duration=duration,
                    aspect_ratio=aspect_ratio
                )

                # 标记这个任务需要使用 HTTP 客户端轮询
                if video_id:
                    return f"http_client:{video_id}"

            except Exception as e:
                print(f"❌ HTTP client failed, falling back to SDK: {e}")
                # 如果 HTTP 客户端失败，继续使用 SDK（只使用第一张图片）

        # 使用 OpenAI SDK（单个图片）
        # 设置视频参数
        video_config = {
            "prompt": prompt,
        }

        # 添加模型参数（默认是 sora-2）
        if model:
            video_config["model"] = model
        else:
            video_config["model"] = "sora-2"

        # 添加可选参数
        if duration:
            video_config["seconds"] = str(duration)

        if resolution:
            # 分辨率转换为 width x height 格式
            resolution_map = {
                "4k": "3840x2160",
                "1080p": "1920x1080",
                "720p": "1280x720",
                # "480p": "854x480",
                "720x1280": "720x1280",      # Sora竖屏
                "1792x1024": "1792x1024",    # Sora宽屏
                "1024x1792": "1024x1792"     # Sora竖屏宽幅
            }
            if resolution in resolution_map:
                video_config["size"] = resolution_map[resolution]
            else:
                # 如果已经是 width x height 格式，直接使用
                if 'x' in resolution and resolution.replace('x', '').isdigit():
                    video_config["size"] = resolution

        # 处理单个图片 - 使用 OpenAI SDK 的 input_reference 参数 (文件路径)
        # 注意：OpenAI SDK 目前仅支持单个 input_reference 参数，不支持数组
        if image_paths and len(image_paths) > 0:
            processed_images = []
            for i, image_path in enumerate(image_paths):
                print(f"🖼️  Processing image reference {i+1}/{len(image_paths)}: {image_path}")
                try:
                    import pathlib
                    path_obj = pathlib.Path(image_path)
                    if not path_obj.exists():
                        raise ValueError(f"Image file not found: {image_path}")

                    # 验证文件类型
                    valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
                    if path_obj.suffix.lower() not in valid_extensions:
                        raise ValueError(f"Invalid image format: {path_obj.suffix}")

                    processed_images.append(Path(image_path))
                    print(f"✅ input_reference {i+1} set using file path: {image_path}")
                except Exception as e:
                    print(f"⚠️  Error processing input_reference {i+1}: {e}")
                    # 如果处理失败，跳过这个图片，继续处理其他图片
                    continue

            # 如果有合法图片，使用第一张
            if processed_images:
                selected_image = processed_images[0]
                video_config["input_reference"] = selected_image
                print(f"✅ Set input_reference for video generation: {selected_image}")

        try:
            # 使用 OpenAI SDK 创建视频
            print(f"📤 Sending video generation request to OpenAI API using SDK...")
            print(f"   Parameters: {list(video_config.keys())}")

            # 调用 OpenAI Video API - SDK 会自动处理文件上传
            response = self.openai_client.videos.create(**video_config)
            video_id = response.id
            print(f"✅ Video task created successfully! ID: {video_id}")
            return video_id

        except openai.APIError as e:
            print(f"❌ OpenAI API error: {e}")
            raise Exception(f"OpenAI API error: {e}")
        except Exception as e:
            print(f"❌ Error creating OpenAI video task: {e}")
            raise Exception(f"Error creating OpenAI video task: {e}")

    async def _poll_openai_video_task(self, task_id: str, use_http_client: bool = False) -> Dict[str, Any]:
        """使用 OpenAI SDK 轮询视频生成任务状态"""
        print(f"⏳ Polling OpenAI video task: {task_id}")

        # 如果使用 HTTP 客户端创建的任务，需要改用 HTTP 轮询
        if use_http_client:
            try:
                result_url = await self.openai_http_client.poll_video_task_completion(video_id=task_id)
                return {'status': 'succeeded', 'result_url': result_url}
            except Exception as e:
                print(f"❌ HTTP client polling failed: {e}")
                raise

        # 使用 OpenAI SDK 轮询
        try:
            while True:
                # 使用 SDK 获取视频状态
                video = self.openai_client.videos.retrieve(task_id)
                print(f"📋 Video status: {video.status}")

                if video.status in ("succeeded", "completed"):
                    # 获取视频结果 URL - 尝试多个可能的属性位置
                    real_url = (getattr(video, "url", None) or
                               getattr(video, "metadata", {}).get("url") if hasattr(video, "metadata") else None or
                               getattr(video, "result", {}).get("url") if hasattr(video, "result") else None)

                    # 如果没有找到 URL，使用默认规则构建视频地址
                    if not real_url:
                        # 构建默认的视频播放地址: {base_url}/v1/videos/{task_id}
                        base_url = self.api_url.rstrip('/')
                        real_url = f"{base_url}/videos/{task_id}/content"
                        print(f"📝 Using default video URL pattern: {real_url}")

                    print(f"✅ Video generation completed: {real_url}")
                    return {'status': 'succeeded', 'result_url': real_url}
                elif video.status == "failed":
                    error_message = getattr(video, 'error', None)
                    if error_message and hasattr(error_message, 'message'):
                        error_detail = error_message.message
                    else:
                        error_detail = str(error_message) if error_message else 'Unknown error'
                    raise Exception(f"Video generation failed: {error_detail}")

                # 等待后继续轮询
                await asyncio.sleep(3.0)

        except openai.APIError as e:
            print(f"❌ OpenAI API error during polling: {e}")
            raise Exception(f"OpenAI API error during polling: {e}")
        except Exception as e:
            print(f"❌ Error polling video task: {e}")
            raise Exception(f"Error polling video task: {e}")

    def _is_configured(self) -> bool:
        """检查 Jaaz API 是否已配置"""
        return bool(self.api_url and self.api_token)

    def _build_headers(self, content_type: Optional[str] = "application/json") -> Dict[str, str]:
        headers = {"Authorization": f"Bearer {self.api_token}"}
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    async def create_magic_task(self, image_content: str) -> str:
        """
        创建云端魔法图像生成任务

        Args:
            image_content: 图片内容（base64 或 URL）

        Returns:
            str: 任务 ID，失败时返回空字符串
        """
        try:
            if not image_content or not image_content.startswith('data:image/'):
                print("❌ Invalid image content format")
                return ""

            async with HttpClient.create_aiohttp() as session:
                async with session.post(
                    f"{self.api_url}/image/magic",
                    headers=self._build_headers(),
                    json={
                        "image": image_content
                    },
                    timeout=aiohttp.ClientTimeout(total=60.0)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        task_id = data.get('task_id', '')
                        if task_id:
                            print(f"✅ Magic task created: {task_id}")
                            return task_id
                        else:
                            print("❌ No task_id in response")
                            return ""
                    else:
                        error_text = await response.text()
                        print(
                            f"❌ Failed to create magic task: {response.status} - {error_text}")
                        return ""

        except Exception as e:
            print(f"❌ Error creating magic task: {e}")
            return ""

    async def create_video_task(
        self,
        prompt: str,
        model: str,
        resolution: Optional[str] = None,
        duration: Optional[int] = None,
        aspect_ratio: Optional[str] = None,
        input_images: Optional[List[str]] = None,
        **kwargs: Any
    ) -> str:
        """
        创建云端视频生成任务

        Args:
            prompt: 视频生成提示词
            model: 视频生成模型
            resolution: 视频分辨率
            duration: 视频时长（秒）
            aspect_ratio: 宽高比
            input_images: 输入图片列表（可选）
            **kwargs: 其他参数

        Returns:
            str: 任务 ID

        Raises:
            Exception: 当任务创建失败时抛出异常
        """
        async with HttpClient.create_aiohttp() as session:
            payload = {
                "prompt": prompt,
                "model": model,
                "resolution": resolution,
                "duration": duration,
                "aspect_ratio": aspect_ratio,
                **kwargs
            }

            if input_images:
                online_image_urls = []

                # Handle online file URLs (dynamically get API URL from environment)
                import os
                base_api_url = os.getenv('BASE_API_URL', 'https://dev.clinx.work').rstrip('/')

                for image_path in input_images:
                    if image_path.startswith(f'{base_api_url}/v1/files/'):
                        # Already an online URL
                        online_image_urls.append(image_path)
                        print(f"Using existing online image: {image_path}")
                    else:
                        # Upload local file to online storage
                        print(f"Uploading local image to online storage: {image_path}")
                        online_image_url = await upload_image_from_file_path(image_path, self.api_token)
                        
                        if not online_image_url:
                            raise ValueError(
                                f"Failed to upload input image: {image_path}. Please check if the image exists and is valid.")

                        online_image_urls.append(online_image_url)
                        print(f"✅ Image uploaded successfully, using online URL: {online_image_url}")

                # Set the images in payload
                payload["images"] = online_image_urls

            async with session.post(
                f"{self.api_url}/video/generations",
                headers=self._build_headers(),
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120.0)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    task_id = data.get('task_id', '')
                    if task_id:
                        print(f"✅ Video task created: {task_id}")
                        return task_id
                    else:
                        raise Exception("No task_id in response")
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to create video task: HTTP {response.status} - {error_text}")

    async def poll_for_task_completion_jaaz(
        self,
        task_id: str,
        max_attempts: Optional[int] = None,
        interval: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        等待任务完成并返回结果

        Args:
            task_id: 任务 ID
            max_attempts: 最大轮询次数
            interval: 轮询间隔（秒）

        Returns:
            Dict[str, Any]: 任务结果

        Raises:
            Exception: 当任务失败或超时时抛出异常
        """
        max_attempts = max_attempts or 150  # 默认最多轮询 150 次
        interval = interval or 2.0  # 默认轮询间隔 2 秒

        async with HttpClient.create_aiohttp() as session:
            for _ in range(max_attempts):
                async with session.get(
                    f"{self.api_url}/video/generations/{task_id}",
                    headers=self._build_headers(),
                    timeout=aiohttp.ClientTimeout(total=20.0)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('success') and data.get('data', {}).get('found'):
                            task = data['data']['task']
                            status = task.get('status')

                            if status == 'succeeded':
                                print(
                                    f"✅ Task {task_id} completed successfully")
                                return task
                            elif status == 'failed':
                                error_msg = task.get('error', 'Unknown error')
                                raise Exception(f"Task failed: {error_msg}")
                            elif status == 'cancelled':
                                raise Exception("Task was cancelled")
                            elif status == 'processing':
                                # 继续轮询
                                await asyncio.sleep(interval)
                                continue
                            else:
                                raise Exception(f"Unknown task status: {status}")
                        else:
                            raise Exception("Task not found")
                    else:
                        raise Exception(f"Failed to get task status: HTTP {response.status}")

            raise Exception(f"Task polling timeout after {max_attempts} attempts")

    # 修改为clinx的task
    async def poll_for_task_completion(
        self,
        task_id: str,
        max_attempts: Optional[int] = None,
        interval: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        等待任务完成并返回结果

        Args:
            task_id: 任务 ID
            max_attempts: 最大轮询次数
            interval: 轮询间隔（秒）

        Returns:
            Dict[str, Any]: 任务结果

        Raises:
            Exception: 当任务失败或超时时抛出异常
        """
        max_attempts = max_attempts or 150  # 默认最多轮询 150 次
        interval = interval or 2.0  # 默认轮询间隔 2 秒

        async with HttpClient.create_aiohttp() as session:
            for _ in range(max_attempts):
                await asyncio.sleep(interval)
                async with session.get(
                        f"{self.api_url}/video/generations/{task_id}",
                        headers=self._build_headers(),
                        timeout=aiohttp.ClientTimeout(total=20.0)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('data', {}).get('status'):
                            status = data['data']['status']

                            if status == 'succeeded' or status == 'SUCCESS':
                                print(
                                    f"✅ Task {task_id} completed successfully")
                                # 构建新的task对象，提取fail_reason作为result_url
                                result_task = {
                                    'status': status,
                                    'task_id': task_id,
                                    'result_url': data['data'].get('fail_reason', '')
                                }
                                return result_task
                            elif status == 'failed':
                                error_msg = task.get('error', 'Unknown error')
                                raise Exception(f"Task failed: {error_msg}")
                            elif status == 'cancelled':
                                raise Exception("Task was cancelled")
                            elif status == 'processing' or status == 'IN_PROGRESS' or status == 'QUEUED' or status == 'SUBMITTED' or status == 'NOT_START':
                                # 继续轮询
                                await asyncio.sleep(interval)
                                continue
                            else:
                                raise Exception(f"Unknown task status: {status}")
                        else:
                            raise Exception("Task not found")
                    else:
                        raise Exception(f"Failed to get task status: HTTP {response.status}")

            raise Exception(f"Task polling timeout after {max_attempts} attempts")

    async def generate_magic_image(self, image_content: str) -> Optional[Dict[str, Any]]:
        """
        生成魔法图像的完整流程

        Args:
            image_content: 图片内容（base64 或 URL）

        Returns:
            Dict[str, Any]: 包含 result_url 的任务结果，失败时返回包含 error 信息的字典
        """
        try:
            # 1. 创建任务
            task_id = await self.create_magic_task(image_content)
            if not task_id:
                print("❌ Failed to create magic task")
                return {"error": "Failed to create magic task"}

            # 2. 等待任务完成
            result = await self.poll_for_task_completion(task_id, max_attempts=120, interval=5.0) # 10 分钟
            if not result:
                print("❌ Magic generation failed")
                return {"error": "Magic generation failed"}

            if not result.get('result_url'):
                error_msg = result.get('error', 'No result URL found')
                print(f"❌ Magic generation failed: {error_msg}")
                return {"error": f"Magic generation failed: {error_msg}"}

            print(
                f"✅ Magic image generated successfully: {result.get('result_url')}")
            return result

        except Exception as e:
            error_msg = f"Error in magic image generation: {str(e)}"
            print(f"❌ {error_msg}")
            return {"error": error_msg}

    async def generate_video_openai(
        self,
        prompt: str,
        model: str,
        resolution: Optional[str] = None,
        duration: Optional[int] = None,
        aspect_ratio: Optional[str] = None,
        input_images: Optional[List[str]] = None,
        ctx: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> str:
        """
        创建OpenAI视频生成任务并同步等待完成
        """
        print(f"🎥 generate_video_openai called with:")
        print(f"  model: {repr(model)}")
        print(f"  prompt: {repr(prompt[:100])}")
        print(f"  input_images: {repr(input_images)}")
        print(f"  resolution: {repr(resolution)}")
        print(f"  duration: {repr(duration)}")
        print(f"  aspect_ratio: {repr(aspect_ratio)}")
        print(f"  ctx: {repr(ctx)[:200]}")

        # Get context for WebSocket notifications
        ctx = ctx or kwargs.get('ctx', {})
        session_id = ctx.get('session_id', '')
        canvas_id = ctx.get('canvas_id', '')
        tool_call_id = ctx.get('tool_call_id', '')
        temp_files = []
        print(f"🎥 Processing tool_call_id: {tool_call_id}")

        try:
            print(f"🚀 Starting OpenAI video generation...")

            # Send start notification if we have session_id
            if session_id:
                await send_video_start_notification(
                    session_id,
                    f"Starting {model} video generation..."
                )

            image_paths = []
            if input_images:
                for i, image_path in enumerate(input_images):
                    print(f"🖼️  Processing input image {i+1}/{len(input_images)}: {image_path}")
                    if image_path.startswith('http'):
                        # 网络图片，下载到临时文件
                        downloaded_path = await self._download_image(image_path)
                        image_paths.append(downloaded_path)
                        temp_files.append(downloaded_path)
                        print(f"✅ Downloaded network image {i+1}: {downloaded_path}")
                    else:
                        # 本地文件路径
                        if os.path.exists(image_path):
                            image_paths.append(image_path)
                            print(f"✅ Using existing local image {i+1}: {image_path}")
                        else:
                            # 尝试在 FILES_DIR 中查找
                            from services.config_service import FILES_DIR
                            local_path = os.path.join(FILES_DIR, image_path)
                            if os.path.exists(local_path):
                                image_paths.append(local_path)
                                print(f"✅ Found local image {i+1} in FILES_DIR: {local_path}")
                            else:
                                print(f"⚠️  Local image not found: {image_path} or {local_path}")
                                print(f"FILES_DIR 内容: {os.listdir(FILES_DIR) if os.path.exists(FILES_DIR) else '目录不存在'}")

            print(f"✅ Total {len(image_paths)} images ready for video generation")
            if image_paths:
                print(f"   Image paths: {image_paths}")

            # 🎯 图像分辨率处理 (对所有模型) + Sora特定验证
            first_img_resolution = None  # 用于记录第一张图片的分辨率

            # 优先读取所有图片的分辨率信息
            if image_paths:
                print("🔍 Reading input image resolutions...")
                for i, img_path in enumerate(image_paths):
                    try:
                        from PIL import Image
                        with Image.open(img_path) as img:
                            img_size = f"{img.width}x{img.height}"
                            print(f"   📊 Image {i+1}: {img_path} -> {img_size}")

                            # 记录第一张图片的分辨率
                            if i == 0:
                                first_img_resolution = img_size
                    except Exception as e:
                        print(f"⚠️  Error reading image resolution for {img_path}: {e}")
                        continue

            # Sora模型特定验证
            if model and 'sora' in model.lower():
                # Sora duration validation
                if duration is not None:
                    allowed_durations = [4, 8, 12]
                    if duration not in allowed_durations:
                        error_msg = f"❌ Duration {duration} is not supported by {model}. Allowed durations: {allowed_durations}"
                        print(error_msg)
                        if session_id:
                            await send_video_error_notification(session_id, error_msg)
                        raise ValueError(error_msg)
                    else:
                        print(f"✅ Duration {duration} is valid for {model}")

                # Sora image分辨率验证
                if first_img_resolution:
                    SORA_VALID_RESOLUTIONS = {"720x1280", "1280x720", "1792x1024", "1024x1792"}
                    print("🔍 Validating image resolution for Sora...")

                    if first_img_resolution not in SORA_VALID_RESOLUTIONS:
                        valid_formats = ", ".join(sorted(SORA_VALID_RESOLUTIONS))
                        error_msg = f"❌ Image resolution {first_img_resolution} is not supported by Sora. Valid resolutions: {valid_formats}"
                        print(error_msg)
                        if session_id:
                            await send_video_error_notification(session_id, error_msg)
                        raise ValueError(error_msg)
                    else:
                        print(f"   ✅ {first_img_resolution} is valid for Sora")

            # 自动设置分辨率逻辑
            if resolution is None and first_img_resolution:
                resolution = first_img_resolution
                print(f"🎯 Auto-setting resolution from first image: {resolution}")
            elif resolution is None and not first_img_resolution and image_paths:
                # 如果没有成功读取到图片分辨率，但确实有图片路径，提供默认分辨率
                resolution = "1280x720"  # Sora支持的默认分辨率
                print(f"🎯 Using default resolution: {resolution} (image reading failed)")
            elif resolution is None:
                # 没有图片时的默认分辨率
                resolution = "720p"
                print(f"🎯 Using default resolution for no-image scenario: {resolution}")

            task_id = await self._create_openai_video_task(
                prompt=prompt,
                model=model,
                image_paths=image_paths if image_paths else None,
                resolution=resolution,
                duration=duration,
                aspect_ratio=aspect_ratio
            )

            print(f"📋 Task created successfully: {task_id}")

            if not task_id:
                raise Exception("Failed to create OpenAI video task")

            # 检查是否使用了 HTTP 客户端
            use_http_client = False
            clean_task_id = task_id

            if task_id.startswith("http_client:"):
                use_http_client = True
                clean_task_id = task_id.replace("http_client:", "")
                print(f"🔗 Detected HTTP client task, will use HTTP client for polling: {clean_task_id}")

            # 立即同步轮询直到完成并返回结果
            print(f"⏳ [tool:{tool_call_id}] Starting polling for task completion...")
            result = await self._poll_openai_video_task(clean_task_id, use_http_client=use_http_client)
            print(f"✅ [tool:{tool_call_id}] Polling completed with result: {result}")

            if not result.get('result_url'):
                raise Exception("No video URL found", task_id)

            # === 只保留纯地址，Canvas 负责落地播放器 ===
            real_url = result['result_url']

            if session_id and canvas_id:
                # 用纯地址走完整流程：下载-保存-推画布-发 WebSocket
                await process_video_result(
                    video_url=real_url,
                    session_id=session_id,
                    canvas_id=canvas_id,
                    provider_name=f"openai_{model}"
                )
                print(f"🎥 [tool:{tool_call_id}] Canvas processed, returning raw url")
                return real_url          # 给外层包 Dict
            else:
                print(f"🎥 [tool:{tool_call_id}] No canvas context, returning raw url")
                return real_url

        except Exception as e:
            print(f"❌ OpenAI video generation error: {e}")
            print(f"   Error type: {type(e)}")
            print(f"   Error details: {e.args}")

            # Send error notification if we have session_id
            if session_id:
                await send_video_error_notification(session_id, str(e))
            raise

        finally:
            for file_path in temp_files:
                if os.path.exists(file_path):
                    os.unlink(file_path)

    async def generate_video(
        self,
        prompt: str,
        model: str,
        resolution: Optional[str] = None,
        duration: Optional[int] = None,
        aspect_ratio: Optional[str] = None,
        input_images: Optional[List[str]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        print(f"🎬 generate_video: model={model}, prompt={prompt[:50]}...")
        if model and ('sora' in model.lower() or 'jimeng' in model.lower()):
            # Get context info for WebSocket notifications if available
            ctx = kwargs.get('ctx', {})
            session_id = ctx.get('session_id', '')
            canvas_id = ctx.get('canvas_id', '')

            print(f"🗂  Detected jimeng/sora model, calling generate_video_openai synchronously...")
            # generate_video_openai 内部已经同步完成所有轮询
            final_message = await self.generate_video_openai(
                prompt=prompt,
                model=model,
                resolution=resolution,
                duration=duration,
                aspect_ratio=aspect_ratio,
                input_images=input_images,
                ctx=ctx
            )
            print(f"🔚 generate_video_openai returned final message: [{final_message[:100]}...]")
            # 保持 Dict 结构，避免下游代码调 .get() 时报错
            return {"result_url": final_message, "status": "succeeded"}

        task_id = await self.create_video_task(
            prompt=prompt,
            model=model,
            resolution=resolution,
            duration=duration,
            aspect_ratio=aspect_ratio,
            input_images=input_images,
            **kwargs
        )

        if not task_id:
            raise Exception("Failed to create video task")

        result = await self.poll_for_task_completion(task_id)
        if not result:
            raise Exception("Video generation failed")

        if result.get('error'):
            raise Exception(f"Video generation failed: {result['error']}")

        if not result.get('result_url'):
            raise Exception("No result URL found in video generation response")

        print(f"✅ Video generated successfully: {result.get('result_url')}")
        return result

    async def generate_video_by_seedance(
        self,
        prompt: str,
        model: str,
        resolution: str = "720p",
        duration: int = 5,
        aspect_ratio: str = "16:9",
        input_images: Optional[List[str]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        使用 Seedance 模型生成视频的完整流程

        Args:
            prompt: 视频生成提示词
            model: 视频生成模型
            resolution: 视频分辨率
            duration: 视频时长（秒）
            aspect_ratio: 宽高比
            input_images: 输入图片列表（可选）
            **kwargs: 其他参数

        Returns:
            Dict[str, Any]: 包含 result_url 的任务结果

        Raises:
            Exception: 当视频生成失败时抛出异常
        """
        # 1. 创建 Seedance 视频生成任务
        async with HttpClient.create_aiohttp() as session:
            payload = {
                "prompt": prompt,
                "model": model,
                "resolution": resolution,
                "duration": duration,
                "aspect_ratio": aspect_ratio,
                **kwargs
            }

            if input_images:
                payload["input_images"] = input_images

            async with session.post(
                f"{self.api_url}/video/seedance/generation",
                headers=self._build_headers(),
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120.0)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    task_id = data.get('task_id', '')
                    if not task_id:
                        raise Exception("No task_id in response")
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to create Seedance video task: HTTP {response.status} - {error_text}")

        print(f"✅ Seedance video task created: {task_id}")

        # 2. 等待任务完成
        result = await self.poll_for_task_completion(task_id)
        if not result:
            raise Exception("Seedance video generation failed")

        if result.get('error'):
            raise Exception(f"Seedance video generation failed: {result['error']}")

        if not result.get('result_url'):
            raise Exception("No result URL found in Seedance video generation response")

        print(
            f"✅ Seedance video generated successfully: {result.get('result_url')}")
        return result

    async def create_midjourney_task(
        self,
        prompt: str,
        model: str = "midjourney",
        **kwargs: Any
    ) -> str:
        """
        创建云端 Midjourney 图像生成任务

        Args:
            prompt: 图像生成提示词
            model: 图像生成模型（默认为 midjourney）
            **kwargs: 其他参数（如 mode 等）

        Returns:
            str: 任务 ID

        Raises:
            Exception: 当任务创建失败时抛出异常
        """
        async with HttpClient.create_aiohttp() as session:
            payload = {
                "prompt": prompt,
                "model": model,
                **kwargs
            }

            async with session.post(
                f"{self.api_url}/image/midjourney/generation",
                headers=self._build_headers(),
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60.0)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    task_id = data.get('task_id', '')
                    if task_id:
                        print(f"✅ Midjourney task created: {task_id}")
                        return task_id
                    else:
                        raise Exception("No task_id in response")
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to create Midjourney task: HTTP {response.status} - {error_text}")

    async def generate_image_by_midjourney(
        self,
        prompt: str,
        model: str = "midjourney",
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        使用 Midjourney 生成图像的完整流程

        Args:
            prompt: 图像生成提示词
            model: 图像生成模型（默认为 midjourney）
            **kwargs: 其他参数（如 mode 等）

        Returns:
            Dict[str, Any]: 包含 result_url 的任务结果

        Raises:
            Exception: 当图像生成失败时抛出异常
        """
        # 1. 创建 Midjourney 图像生成任务
        task_id = await self.create_midjourney_task(
            prompt=prompt,
            model=model,
            **kwargs
        )

        if not task_id:
            raise Exception("Failed to create Midjourney task")

        # 2. 等待任务完成
        task_result = await self.poll_for_task_completion(task_id, max_attempts=150, interval=2.0)
        print(f"🎨 Midjourney task result: {task_result}")
        if not task_result:
            raise Exception("Midjourney image generation failed")

        if task_result.get('error'):
            raise Exception(f"Midjourney image generation failed: {task_result['error']}")

        if not task_result.get('result'):
            raise Exception("No result found in Midjourney image generation response")

        result = task_result.get('result')
        print(f"✅ Midjourney image generated successfully: {result}")
        return result or {}

    def is_configured(self) -> bool:
        """
        检查服务是否已正确配置

        Returns:
            bool: 配置是否有效
        """
        return self._is_configured()
