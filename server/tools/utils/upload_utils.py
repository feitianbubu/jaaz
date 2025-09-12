import os
import aiohttp
import base64
from PIL import Image
from io import BytesIO
from typing import Optional
import tempfile
import uuid


async def upload_image_to_clinx(image_data: str, api_token: str = '') -> Optional[str]:
    """
    Upload image to Clinx online file storage and return the URL.
    
    Args:
        image_data: Base64 encoded image data (with or without data URL prefix)
        api_token: Authorization token for the API (optional)
        
    Returns:
        Online URL of the uploaded image, or None if upload fails
    """
    try:
        # Extract base64 data from data URL if needed
        if image_data.startswith('data:'):
            image_data = image_data.split(',')[1]
        
        # Decode base64 image
        image_bytes = base64.b64decode(image_data)
        
        # Open image to determine format
        image = Image.open(BytesIO(image_bytes))
        img_format = image.format.lower() if image.format else 'png'
        
        # Create temporary file for upload
        with tempfile.NamedTemporaryFile(suffix=f'.{img_format}', delete=False) as tmp_file:
            tmp_file.write(image_bytes)
            tmp_file_path = tmp_file.name
        
        try:
            # Get API URL from environment variable
            base_api_url = os.getenv('BASE_API_URL', 'https://newapi.clinx.work').rstrip('/')
            upload_url = f"{base_api_url}/v1/files"
            
            with open(tmp_file_path, 'rb') as f:
                # Prepare form data while file is open
                form_data = aiohttp.FormData()
                form_data.add_field('file', f, filename=f'{uuid.uuid4()}.{img_format}')
                form_data.add_field('purpose', 'user_data')
                form_data.add_field('expires_after', '{"anchor":"created_at","seconds":86400}')
                
                # Prepare headers
                headers = {}
                if api_token:
                    headers['Authorization'] = f"Bearer {api_token}"
                # aiohttp handles Content-Type for multipart/form-data automatically
                
                # Make upload request while file is still open
                async with aiohttp.ClientSession() as session:
                    async with session.post(upload_url, data=form_data, headers=headers) as response:
                        if response.status == 200:
                            result = await response.json()
                            if result.get('code') == 0 and result.get('data'):
                                file_id = result['data'].get('id')
                                if file_id:
                                    # Construct file URL
                                    file_url = f"{base_api_url}/v1/files/{file_id}/content"
                                    print(f"✅ Image uploaded successfully: {file_url}")
                                    return file_url
                            else:
                                print(f"❌ Upload failed with response: {result}")
                        else:
                            error_text = await response.text()
                            print(f"❌ Upload request failed with status {response.status}: {error_text}")
            
            return None
        
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)
  
    except Exception as e:
        print(f"❌ Error uploading image to Clinx: {e}")
        return None
async def upload_image_direct(file_path: str, api_token: str = '') -> Optional[str]:
    """
    Upload image file directly from local path to Clinx online storage (without base64 encoding).
    
    Args:
        file_path: Local file path to the image (relative or absolute)
        api_token: Authorization token for the API (optional)
        
    Returns:
        Online URL of the uploaded image, or None if upload fails
    """
    try:
        # Check if it's a relative path and construct full path
        if not os.path.isabs(file_path):
            # This is a relative path, need to add FILES_DIR
            from services.config_service import FILES_DIR
            full_path = os.path.join(FILES_DIR, file_path)
        else:
            full_path = file_path

        print(f"Uploading image file from: {full_path}")
        
        # Verify file exists
        if not os.path.exists(full_path):
            print(f"❌ File not found: {full_path}")
            return None
            
        # Verify it's an image file
        try:
            with Image.open(full_path) as img:
                img_format = img.format.lower() if img.format else 'png'
                print(f"Image format detected: {img_format}")
        except Exception as e:
            print(f"❌ Invalid image file: {e}")
            return None
        
        # Get API URL from environment variable
        base_api_url = os.getenv('BASE_API_URL', 'https://newapi.clinx.work').rstrip('/')
        upload_url = f"{base_api_url}/v1/files"
        
        # Determine file extension
        ext = os.path.splitext(file_path)[1].lower()
        if not ext:
            ext = f'.{img_format}'
        
        with open(full_path, 'rb') as f:
            # Prepare form data with original filename for better tracking
            original_name = os.path.basename(file_path)
            form_data = aiohttp.FormData()
            form_data.add_field('file', f, filename=f"{uuid.uuid4()}_{original_name}")
            form_data.add_field('purpose', 'user_data')
            form_data.add_field('expires_after', '{"anchor":"created_at","seconds":86400}')
            
            # Prepare headers
            headers = {}
            if api_token:
                headers['Authorization'] = f"Bearer {api_token}"
            
            # Make upload request
            async with aiohttp.ClientSession() as session:
                async with session.post(upload_url, data=form_data, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get('code') == 0 and result.get('data'):
                            file_id = result['data'].get('id')
                            if file_id:
                                # Construct file URL
                                file_url = f"{base_api_url}/v1/files/{file_id}/content"
                                print(f"✅ Image uploaded successfully: {file_url}")
                                return file_url
                        else:
                            print(f"❌ Upload failed with response: {result}")
                    else:
                        error_text = await response.text()
                        print(f"❌ Upload request failed with status {response.status}: {error_text}")
        
        return None
        
    except Exception as e:
        print(f"❌ Error uploading file from path: {e}")
        return None



async def upload_image_from_file_path(file_path: str, api_token: str = '') -> Optional[str]:
    """
    Upload image file from local path to Clinx online storage (legacy method with base64).
    
    Args:
        file_path: Local file path to the image
        api_token: Authorization token for the API (optional)
        
    Returns:
        Online URL of the uploaded image, or None if upload fails
    """
    try:
        # Check if it's a relative path and construct full path
        if not os.path.isabs(file_path):
            # This is a relative path, need to add FILES_DIR
            from services.config_service import FILES_DIR
            full_path = os.path.join(FILES_DIR, file_path)
        else:
            full_path = file_path

        print(f"Uploading image file from: {full_path}")
        
        # Verify file exists
        if not os.path.exists(full_path):
            print(f"❌ File not found: {full_path}")
            return None
            
        # Verify it's an image file
        try:
            with Image.open(full_path) as img:
                img_format = img.format.lower() if img.format else 'png'
                print(f"Image format detected: {img_format}")
        except Exception as e:
            print(f"❌ Invalid image file: {e}")
            return None
        
        # Get API URL from environment variable
        base_api_url = os.getenv('BASE_API_URL', 'https://newapi.clinx.work').rstrip('/')
        upload_url = f"{base_api_url}/v1/files"
        
        # Determine file extension
        ext = os.path.splitext(file_path)[1].lower()
        if not ext:
            ext = f'.{img_format}'
        
        with open(full_path, 'rb') as f:
            # Prepare form data with original filename for better tracking
            original_name = os.path.basename(file_path)
            form_data = aiohttp.FormData()
            form_data.add_field('file', f, filename=f"{uuid.uuid4()}_{original_name}")
            form_data.add_field('purpose', 'user_data')
            form_data.add_field('expires_after', '{"anchor":"created_at","seconds":86400}')
            
            # Prepare headers
            headers = {}
            if api_token:
                headers['Authorization'] = f"Bearer {api_token}"
            
            # Make upload request
            async with aiohttp.ClientSession() as session:
                async with session.post(upload_url, data=form_data, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get('code') == 0 and result.get('data'):
                            file_id = result['data'].get('id')
                            if file_id:
                                # Construct file URL
                                file_url = f"{base_api_url}/v1/files/{file_id}/content"
                                print(f"✅ Image uploaded successfully: {file_url}")
                                return file_url
                        else:
                            print(f"❌ Upload failed with response: {result}")
                    else:
                        error_text = await response.text()
                        print(f"❌ Upload request failed with status {response.status}: {error_text}")
        
        return None
        
    except Exception as e:
        print(f"❌ Error uploading file from path: {e}")
        return None


async def upload_image_from_file_path(file_path: str, api_token: str = '') -> Optional[str]:
    """
    Upload image file from local path to Clinx online storage.
    
    Args:
        file_path: Local file path to the image
        api_token: Authorization token for the API (optional)
        
    Returns:
        Online URL of the uploaded image, or None if upload fails
    """
    try:
        # Check if it's a relative path and construct full path
        if not os.path.isabs(file_path):
            # This is a relative path, need to add FILES_DIR
            from services.config_service import FILES_DIR
            full_path = os.path.join(FILES_DIR, file_path)
        else:
            full_path = file_path

        print(f"Uploading image file from: {full_path}")
        
        # Get API URL from environment variable
        base_api_url = os.getenv('BASE_API_URL', 'https://newapi.clinx.work').rstrip('/')
        upload_url = f"{base_api_url}/v1/files"
        
        # Determine file extension for naming
        ext = os.path.splitext(file_path)[1].lower()
        if not ext:
            ext = '.png'
        
        with open(full_path, 'rb') as f:
            # Prepare form data while file is open
            form_data = aiohttp.FormData()
            form_data.add_field('file', f, filename=f'{uuid.uuid4()}{ext}')
            form_data.add_field('purpose', 'user_data')
            form_data.add_field('expires_after', '{"anchor":"created_at","seconds":86400}')
            
            # Prepare headers
            headers = {}
            if api_token:
                headers['Authorization'] = f"Bearer {api_token}"
            
            # Make upload request while file is still open
            async with aiohttp.ClientSession() as session:
                async with session.post(upload_url, data=form_data, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get('code') == 0 and result.get('data'):
                            file_id = result['data'].get('id')
                            if file_id:
                                # Construct file URL
                                file_url = f"{base_api_url}/v1/files/{file_id}/content"
                                print(f"✅ Image uploaded successfully: {file_url}")
                                return file_url
                        else:
                            print(f"❌ Upload failed with response: {result}")
                    else:
                        error_text = await response.text()
                        print(f"❌ Upload request failed with status {response.status}: {error_text}")
        
        return None
        
    except Exception as e:
        print(f"❌ Error uploading file from path: {e}")
        return None