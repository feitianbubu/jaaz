from typing import Optional
import os
import traceback
import base64
from .base import ImageGenerator, get_image_info_and_save, generate_image_id
from services.config_service import FILES_DIR
from utils.http_client import HttpClient

class ClinxGenerator(ImageGenerator):
    """Clinx image generator implementation (OpenAI compatible, use user access_token)"""

    async def generate(
        self,
        prompt: str,
        model: str,
        aspect_ratio: str = "1:1",
        input_image: Optional[str] = None,
        access_token: Optional[str] = None,
        **kwargs
    ) -> tuple[str, int, int, str]:
        try:
            if not access_token:
                raise ValueError("Clinx access_token is required for image generation")
            url = "https://newapi.clinx.work/v1/images/generations"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            data = {
                "model": model,
                "prompt": prompt,
                "n": kwargs.get("num_images", 1),
                "size": kwargs.get("size", "auto"),
            }
            if aspect_ratio:
                data["aspect_ratio"] = aspect_ratio
            # 处理输入图片
            if input_image:
                if input_image.startswith('data:'):
                    data['input_image'] = input_image
                else:
                    with open(input_image, 'rb') as image_file:
                        image_data = image_file.read()
                        image_b64 = base64.b64encode(image_data).decode('utf-8')
                        data['input_image'] = image_b64
            async with HttpClient.create() as client:
                response = await client.post(url, headers=headers, json=data)
                if response.status_code != 200:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    print(f'🦄 Clinx API error: {error_msg}')
                    raise Exception(f'Image generation failed: {error_msg}')
                res = response.json()
            # 兼容OpenAI格式响应
            if 'data' in res and len(res['data']) > 0:
                image_data = res['data'][0]
                if 'b64_json' in image_data:
                    image_b64 = image_data['b64_json']
                    image_id = generate_image_id()
                    mime_type, width, height, extension = await get_image_info_and_save(
                        image_b64,
                        os.path.join(FILES_DIR, f'{image_id}'),
                        is_b64=True
                    )
                    filename = f'{image_id}.{extension}'
                    return mime_type, width, height, filename
                elif 'url' in image_data:
                    image_url = image_data['url']
                    image_id = generate_image_id()
                    mime_type, width, height, extension = await get_image_info_and_save(
                        image_url,
                        os.path.join(FILES_DIR, f'{image_id}')
                    )
                    filename = f'{image_id}.{extension}'
                    return mime_type, width, height, filename
            error_detail = res.get('error', res.get('detail', 'Unknown error'))
            raise Exception(f'Clinx image generation failed: {error_detail}')
        except Exception as e:
            print('Error generating image with Clinx:', e)
            traceback.print_exc()
            raise e 