import { getAccessToken } from './auth'

export type ModelInfo = {
  provider: string
  model: string
  type: 'text' | 'image' | 'tool' | 'video'
  url: string
}

export type ToolInfo = {
  provider: string
  id: string
  display_name?: string | null
  type?: 'image' | 'tool' | 'video'
}

export async function listModels(): Promise<{
  llm: ModelInfo[]
  tools: ToolInfo[]
}> {
  const token = getAccessToken();
  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  const modelsResp = await fetch('/api/list_models', {
    headers
  })
    .then((res) => res.json())
    .catch((err) => {
      console.error(err)
      return []
    })
  const toolsResp = await fetch('/api/list_tools')
    .then((res) => res.json())
    .catch((err) => {
      console.error(err)
      return []
    })

  return {
    llm: modelsResp,
    tools: toolsResp,
  }
}
