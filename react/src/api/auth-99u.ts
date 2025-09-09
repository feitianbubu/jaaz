// 99u authentication service
// 独立的99u登录逻辑，不修改原有auth.ts文件

export interface Auth99uConfig {
  authUrl: string
  clientId: string
  redirectUri: string
  verifyApiUrl: string
}

export interface Auth99uUser {
  id: number
  username: string
  access_token: string
  role?: number
}

export interface Auth99uResponse {
  success: boolean
  data?: Auth99uUser
  message?: string
}

// 99u登录配置
export const AUTH_99U_CONFIG: Auth99uConfig = {
  authUrl: import.meta.env.VITE_AUTH_99U_AUTH_URL || 'https://uc-component.101.com',
  clientId: import.meta.env.VITE_AUTH_99U_CLIENT_ID,
  redirectUri: window.location.origin + (import.meta.env.VITE_AUTH_99U_REDIRECT_URI || '/99u-callback'),
  verifyApiUrl: import.meta.env.VITE_AUTH_99U_VERIFY_API_URL
}

/**
 * 启动99u OAuth登录流程
 * 构建登录URL并跳转到99u认证服务器
 */
export function start99uLogin(): void {
  const params = new URLSearchParams({
    re_login: 'true',
    redirect_type: 'window',
    send_uckey: 'true',
    redirect_uri: AUTH_99U_CONFIG.redirectUri,
    'sdp-app-id': AUTH_99U_CONFIG.clientId,
    lang: 'zh-CN',
  })
  
  const loginUrl = `${AUTH_99U_CONFIG.authUrl}/?${params.toString()}#/login`
  window.location.href = loginUrl
}

/**
 * 处理99u回调，用uckey换取access_token
 * @param uckey 99u返回的授权码
 * @returns Promise<Auth99uResponse>
 */
export async function verify99uToken(uckey: string): Promise<Auth99uResponse> {
  try {
    const response = await fetch(`${AUTH_99U_CONFIG.verifyApiUrl}?code=${encodeURIComponent(uckey)}`)
    const data = await response.json()
    
    if (data.success && data.data) {
      return {
        success: true,
        data: data.data
      }
    } else {
      return {
        success: false,
        message: data.message || '未知错误'
      }
    }
  } catch (error) {
    return {
      success: false,
      message: '验证请求失败'
    }
  }
}

/**
 * 将99u用户信息转换为系统UserInfo格式
 * @param auth99uUser 99u用户信息
 * @returns UserInfo 系统用户信息格式
 */
export function convert99uUserToUserInfo(auth99uUser: Auth99uUser) {
  return {
    id: String(auth99uUser.id),
    username: auth99uUser.username,
    email: '',  // 99u没有email字段
    image_url: '',  // 99u没有image_url字段
    provider: '99u',
    role: auth99uUser.role ?? 0,
  }
}

/**
 * 从URL参数中提取uckey
 * @returns string | null
 */
export function extractUckeyFromUrl(): string | null {
  const params = new URLSearchParams(window.location.search)
  return params.get('uckey')
}