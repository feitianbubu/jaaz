#!/usr/bin/env python3
"""
测试多张图片视频生成的示例脚本

使用 OpenAI HTTP 客户端同时支持多个 input_reference
"""

import asyncio
import os
from pathlib import Path
import sys
from openai_video_http_client import OpenAIVideoHttpClient

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent))


async def test_multiple_images():
    """测试多张图片视频生成"""

    # 配置 API 密钥和基础地址
    api_key = os.getenv("OPENAI_API_KEY", "your-api-key-here")
    base_url = "https://api.openai.com"  # 或者自定义的 OpenAI 兼容 API 地址

    # 初始化 HTTP 客户端
    client = OpenAIVideoHttpClient(api_key=api_key, base_url=base_url)

    # 准备测试图片路径（请确保这些图片存在）
    test_images = [
        "/path/to/image1.jpg",
        "/path/to/image2.jpg",
        "/path/to/image3.jpg"
    ]

    # 确保图片存在
    valid_images = []
    for img_path in test_images:
        if os.path.exists(img_path):
            valid_images.append(img_path)
        else:
            print(f"⚠️  图片不存在: {img_path}")

    if not valid_images:
        print("❌ 没有有效的测试图片")
        return

    print(f"🚀 测试多张图片视频生成（{len(valid_images)} 张图片）...")

    try:
        # 创建视频任务
        prompt = "一只花猫在舞台上优雅地弹奏钢琴，古典风格照明"
        model = "sora-2"

        video_id = await client.create_video_with_multiple_images(
            prompt=prompt,
            model=model,
            image_paths=valid_images,
            resolution="1080p",
            duration=8,
            aspect_ratio="16:9"
        )

        print(f"✅ 视频任务创建成功！ID: {video_id}")

        # 轮询等待完成
        print(f"⏳ 开始轮询任务状态...")
        result_url = await client.poll_video_task_completion(video_id=video_id)

        print(f"🎉 视频生成完成！")
        print(f"📹 视频地址: {result_url}")

        # 可选：获取任务详情
        task_details = await client.retrieve_video_task(video_id)
        print(f"📊 任务详情: {task_details}")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


async def test_single_vs_multiple():
    """对比测试：单图和多图"""

    api_key = os.getenv("OPENAI_API_KEY", "your-api-key-here")
    base_url = "https://api.openai.com"
    client = OpenAIVideoHttpClient(api_key=api_key, base_url=base_url)

    # 测试单图（使用 SDK）
    print("=== 测试单图视频 ===")
    try:
        # 这里使用 JaazService 的 SDK 方法测试
        from jaaz_service import JaazService
        service = JaazService(token=api_key)

        result = await service._create_openai_video_task(
            prompt="一只可爱的小狗在公园奔跑",
            model="sora-2",
            image_paths=[
                "/path/to/single_image.jpg"
            ],
            resolution="1080p",
            duration=6
        )
        print(f"✅ 单图 SDK 任务创建成功: {result}")

    except Exception as e:
        print(f"❌ 单图 SDK 测试失败: {e}")

    # 测试多图（使用 HTTP 客户端）
    print("\n=== 测试多图视频 ===")
    try:
        result = await client.create_video_with_multiple_images(
            prompt="结合多张图片的创意视频",
            model="sora-2",
            image_paths=[
                "/path/to/image1.jpg",
                "/path/to/image2.jpg"
            ],
            resolution="1080p",
            duration=10
        )
        print(f"✅ 多图 HTTP 客户端任务创建成功: {result}")

    except Exception as e:
        print(f"❌ 多图 HTTP 客户端测试失败: {e}")


if __name__ == "__main__":
    print("🚀 OpenAI Video API 多图测试开始")
    print("=" * 50)

    # 运行测试
    asyncio.run(test_multiple_images())

    # 也可以运行对比测试
    # asyncio.run(test_single_vs_multiple())

    print("\n✅ 测试完成")