import asyncio
import aiohttp
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import json
from aiohttp import FormData
import mimetypes
from utils.http_client import HttpClient


class OpenAIVideoHttpClient:
    """OpenAI Video API HTTP 客户端 - 支持多个 input_reference

    当 OpenAI SDK 不支持某些特性时使用原始 HTTP 请求
    """

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com"):
        """初始化 HTTP 客户端

        Args:
            api_key: OpenAI API 密钥
            base_url: API 基础地址，默认为 https://api.openai.com
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.HEADERS = {
            "Authorization": f"Bearer {self.api_key}",
        }

    def _guess_mime_type(self, file_path: str) -> str:
        """猜测文件的 MIME 类型"""
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type is None:
            # 默认为二进制流
            mime_type = "application/octet-stream"
        return mime_type

    async def create_video_with_multiple_images(
        self,
        prompt: str,
        model: str,
        image_paths: List[Union[str, Path]],
        resolution: Optional[str] = None,
        duration: Optional[int] = None,
        aspect_ratio: Optional[str] = None,
        **kwargs: Any
    ) -> str:
        """使用 HTTP 协议创建视频生成任务（支持多个 input_reference）

        Args:
            prompt: 视频生成提示词
            model: 视频生成模型（如 sora-2）
            image_paths: 输入图片路径列表
            resolution: 视频分辨率（可选）
            duration: 视频时长（秒，可选）
            aspect_ratio: 宽高比（可选）
            **kwargs: 其他参数

        Returns:
            str: 视频任务 ID

        Raises:
            Exception: 创建任务失败时抛出异常
        """
        print(f"🎬 使用 HTTP 客户端创建视频任务（支持多个 input_reference）：")
        print(f"  model: {repr(model)}")
        print(f"  prompt: {repr(prompt[:100])}")
        print(f"  image_paths: {repr(image_paths)}")
        print(f"  resolution: {repr(resolution)}")
        print(f"  duration: {repr(duration)}")
        print(f"  aspect_ratio: {repr(aspect_ratio)}")

        if not image_paths:
            raise ValueError("image_paths 不能为空，至少需要一张图片")

        # 准备 formdata 数据
        form_data = FormData()

        # 添加基本参数
        form_data.add_field('model', model)
        form_data.add_field('prompt', prompt)

        # 添加其他可选参数
        if duration:
            form_data.add_field('seconds', str(duration))

        if resolution:
            # 分辨率转换为 width x height 格式
            resolution_map = {
                "4k": "3840x2160",
                "1080p": "1920x1080",
                "720p": "1280x720",
                "480p": "854x480",
                "720x1280": "720x1280",      # Sora竖屏
                "1792x1024": "1792x1024",    # Sora宽屏
                "1024x1792": "1024x1792"     # Sora竖屏宽幅
            }
            if resolution in resolution_map:
                form_data.add_field('size', resolution_map[resolution])
            else:
                # 如果已经是 width x height 格式，直接使用
                if 'x' in resolution and resolution.replace('x', '').isdigit():
                    form_data.add_field('size', resolution)

        if aspect_ratio:
            # 宽高比参数（如果后端支持）
            form_data.add_field('aspect_ratio', aspect_ratio)

        # 处理多张图片引用
        valid_images = []
        for i, image_path in enumerate(image_paths):
            try:
                path_obj = Path(image_path)
                if not path_obj.exists():
                    print(f"⚠️  图片不存在: {image_path}")
                    continue

                # 验证文件类型
                valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
                if path_obj.suffix.lower() not in valid_extensions:
                    print(f"⚠️  不支持的图片格式: {path_obj.suffix}")
                    continue

                mime_type = self._guess_mime_type(str(image_path))

                # 添加 input_reference 字段
                form_data.add_field(
                    'input_reference',
                    open(image_path, 'rb'),
                    filename=path_obj.name,
                    content_type=mime_type
                )

                valid_images.append(str(image_path))
                print(f"📸 已添加 input_reference {i+1}: {image_path}")

            except Exception as e:
                print(f"⚠️  处理图片 {i+1} 时出错: {e}")
                continue

        if not valid_images:
            raise ValueError("没有有效的图片可以上传")

        print(f"✅ 共添加了 {len(valid_images)} 个 input_reference")

        # 发送请求
        url = f"{self.base_url}/videos"
        headers = self.HEADERS.copy()
        # 移除 Content-Type 头，让 aiohttp 自动设置 multipart boundary
        # headers.pop('Content-Type', None)

        try:
            async with HttpClient.create_aiohttp() as session:
                async with session.post(
                    url,
                    headers=headers,
                    data=form_data,
                    timeout=aiohttp.ClientTimeout(total=120.0)
                ) as response:
                    if 200 <= response.status < 300:
                        data = await response.json()
                        video_id = data.get('id')
                        if video_id:
                            print(f"✅ 视频任务创建成功！ID: {video_id}")
                            return video_id
                        else:
                            raise ValueError("响应中缺少 video ID")
                    else:
                        error_text = await response.text()
                        raise ValueError(f"HTTP {response.status}: {error_text}")

        except aiohttp.ClientError as e:
            raise Exception(f"网络请求错误: {e}")
        except Exception as e:
            raise Exception(f"创建视频任务时出错: {e}")

    async def retrieve_video_task(self, video_id: str) -> Dict[str, Any]:
        """获取视频任务状态

        Args:
            video_id: 视频任务 ID

        Returns:
            Dict[str, Any]: 视频任务信息

        Raises:
            Exception: 获取任务失败时抛出异常
        """
        url = f"{self.base_url}/videos/{video_id}"

        try:
            async with HttpClient.create_aiohttp() as session:
                async with session.get(
                    url,
                    headers=self.HEADERS,
                    timeout=aiohttp.ClientTimeout(total=30.0)
                ) as response:
                    if 200 <= response.status < 300:
                        data = await response.json()
                        return data
                    else:
                        error_text = await response.text()
                        raise ValueError(f"HTTP {response.status}: {error_text}")

        except aiohttp.ClientError as e:
            raise Exception(f"网络请求错误: {e}")
        except Exception as e:
            raise Exception(f"获取任务状态时出错: {e}")

    async def poll_video_task_completion(self, video_id: str, max_attempts: int = 300, poll_interval: float = 3.0) -> str:
        """轮询视频任务直到完成

        Args:
            video_id: 视频任务 ID
            max_attempts: 最大轮询次数（默认 300 次，约 15 分钟）
            poll_interval: 轮询间隔（秒，默认 3.0 秒）

        Returns:
            str: 视频结果 URL

        Raises:
            Exception: 任务失败或超时
        """
        print(f"⏳ 开始轮询视频任务: {video_id}")

        attempt = 1
        while attempt <= max_attempts:
            try:
                result = await self.retrieve_video_task(video_id)
                status = result.get('status', result.get('state', 'unknown'))

                print(f"📋 第 {attempt} 次轮询，状态: {status}")

                if status in ["succeeded", "completed", "done"]:
                    # 优先检查 metadata.url（新格式），然后检查传统字段
                    metadata = result.get('metadata', {})
                    video_url = metadata.get('url') or result.get('url') or result.get('result_url') or result.get('output_url')
                    if video_url:
                        print(f"✅ 视频生成完成！URL: {video_url}")
                        return video_url
                    else:
                        raise ValueError("视频生成完成但没有返回 URL")

                elif status in ["failed", "error"]:
                    error_message = result.get('error', '未知错误')
                    raise ValueError(f"视频生成失败: {error_message}")

                elif status == "cancelled":
                    raise ValueError("视频任务已被取消")

                elif status in ["processing", "in_progress", "queued"]:
                    # 继续等待
                    await asyncio.sleep(poll_interval)
                    attempt += 1
                    continue

                else:
                    print(f"⚠️  未知状态: {status}，等待 {poll_interval} 秒后继续")
                    await asyncio.sleep(poll_interval)
                    attempt += 1

            except Exception as e:
                if "failed" in str(e).lower() or "error" in str(e).lower() or "cancelled" in str(e).lower():
                    raise  # 直接抛出任务失败相关的异常

                # 网络或其他临时错误，等待后重试
                print(f"⏳ 第 {attempt} 次轮询遇到临时错误: {e}")
                await asyncio.sleep(poll_interval)
                attempt += 1

        raise TimeoutError(f"轮询超时（{max_attempts} 次轮询，约 {max_attempts * poll_interval} 秒）")

    async def create_video_and_poll(
        self,
        prompt: str,
        model: str,
        image_paths: List[Union[str, Path]],
        resolution: Optional[str] = None,
        duration: Optional[int] = None,
        aspect_ratio: Optional[str] = None,
        max_poll_attempts: int = 300,
        poll_interval: float = 3.0,
        **kwargs: Any
    ) -> str:
        """一体化方法：创建视频任务并等待完成

        Args:
            prompt: 视频生成提示词
            model: 视频生成模型
            image_paths: 输入图片路径列表
            resolution: 视频分辨率（可选）
            duration: 视频时长（秒，可选）
            aspect_ratio: 宽高比（可选）
            max_poll_attempts: 最大轮询次数
            poll_interval: 轮询间隔（秒）
            **kwargs: 其他参数

        Returns:
            str: 视频结果 URL

        Raises:
            Exception: 任务创建失败或生成失败时抛出异常
        """
        # 先创建任务
        video_id = await self.create_video_with_multiple_images(
            prompt=prompt,
            model=model,
            image_paths=image_paths,
            resolution=resolution,
            duration=duration,
            aspect_ratio=aspect_ratio,
            **kwargs
        )

        # 再轮询直到完成
        result_url = await self.poll_video_task_completion(
            video_id=video_id,
            max_attempts=max_poll_attempts,
            poll_interval=poll_interval
        )

        return result_url