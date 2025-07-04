import { getAccessToken } from './auth'

export async function listModels(): Promise<
  {
    provider: string
    model: string
    type: string
    url?: string
    priority?: number
  }[]
> {
  const token = getAccessToken()
  const headers: Record<string, string> = {}
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  const response = await fetch('/api/list_models', { headers })
  return await response.json()
}
