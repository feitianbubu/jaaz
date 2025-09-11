import { compressImageFile } from '@/utils/imageUtils'
import { getAccessToken } from './auth'

export async function uploadImage(
  file: File
): Promise<{ file_id: string; width: number; height: number; url: string }> {
  // Compress image before upload
  const compressedFile = await compressImageFile(file)

  const formData = new FormData()
  formData.append('file', compressedFile)
  const token = getAccessToken()
  const response = await fetch('/api/upload_image', {
    method: 'POST',
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
    body: formData,
  })
  return await response.json()
}
