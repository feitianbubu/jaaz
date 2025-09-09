import React, { useEffect } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { saveAuthData } from '../api/auth'
import { extractUckeyFromUrl, verify99uToken, convert99uUserToUserInfo } from '../api/auth-99u'

/**
 * 99u OAuth回调页面组件
 * 处理99u登录回调，验证uckey并保存用户信息
 */
function RouteComponent() {
  useEffect(() => {
    handleAuth99uCallback()
  }, [])

  /**
   * 处理99u登录回调逻辑
   */
  const handleAuth99uCallback = async () => {
    const uckey = extractUckeyFromUrl()
    
    if (!uckey) {
      alert('未获取到uckey参数')
      window.location.replace('/')
      return
    }

    try {
      // 用uckey换取access_token
      const response = await verify99uToken(uckey)
      
      if (response.success && response.data) {
        // 转换用户信息格式并保存
        const userInfo = convert99uUserToUserInfo(response.data)
        saveAuthData(response.data.access_token, userInfo)
        
        // 跳转到首页
        window.location.replace('/')
      } else {
        alert('登录失败: ' + (response.message || '未知错误'))
        window.location.replace('/')
      }
    } catch (error) {
      console.error('99u login callback error:', error)
      alert('验证请求失败')
      window.location.replace('/')
    }
  }

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto mb-4"></div>
        <p>正在验证99u登录...</p>
      </div>
    </div>
  )
}

/**
 * 99u回调路由定义
 */
export const Route = createFileRoute('/99u-callback')({
  component: RouteComponent,
})