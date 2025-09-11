import { LLMConfig } from '@/types/types'
import { getAccessToken, authenticatedFetch } from './auth'

export async function getConfigExists(): Promise<{ exists: boolean }> {
  const response = await authenticatedFetch('/api/config/exists')
  return await response.json()
}

export async function getConfig(): Promise<{ [key: string]: LLMConfig }> {
  const response = await authenticatedFetch('/api/config')
  return await response.json()
}

export async function updateConfig(config: {
  [key: string]: LLMConfig
}): Promise<{ status: string; message: string }> {
  const response = await authenticatedFetch('/api/config', {
    method: 'POST',
    body: JSON.stringify(config),
  })
  return await response.json()
}

// Update jaaz provider api_key after login (JWT-based)
// Update jaaz provider api_key after login (JWT-based)
export async function updateJaazApiKey(token: string): Promise<void> {
  try {
    const response = await authenticatedFetch('/api/config/jaaz-api-key', {
      method: 'POST',
      body: JSON.stringify({ token })
    })
    
    const result = await response.json()
    if (result.status !== 'success') {
      throw new Error(result.message || 'Failed to update API key')
    }
    
    console.log('✅ Successfully updated jaaz provider api_key:', result.message)
  } catch (error) {
    console.error('❌ Error updating jaaz provider api_key:', error)
    throw error
  }
}

// Clear jaaz provider api_key after logout (JWT-based)
export async function clearJaazApiKey(token?: string): Promise<void> {
  try {
    if (token) {
      // 清除用户会话配置
      const response = await authenticatedFetch('/api/config/user-session', {
        method: 'DELETE',
        body: JSON.stringify({ token })
      })
      
      const result = await response.json()
      if (result.status !== 'success') {
        throw new Error(result.message || 'Failed to clear user session')
      }
      
      console.log('✅ Successfully cleared user session:', result.message)
    } else {
      // 向后兼容：清除全局配置
      const config = await getConfig()
      if (config.jaaz) {
        config.jaaz.api_key = ''
        await updateConfig(config)
        console.log('✅ Successfully cleared global jaaz provider api_key')
      }
    }
  } catch (error) {
    console.error('❌ Error clearing jaaz provider api_key:', error)
    throw error
  }
}
