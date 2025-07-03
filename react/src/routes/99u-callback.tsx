import React, { useEffect } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { saveAuthData } from '../api/auth'

function RouteComponent() {
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const uckey = params.get('uckey')
    function saveUserInfo(user: { id: number, username: string, access_token: string, role?: number }) {
      // 兼容99u返回结构，假设没有email和image_url
      saveAuthData(user.access_token, {
        id: String(user.id),
        username: user.username,
        email: '',
        image_url: '',
        provider: '99u',
        role: user.role ?? 0,
      })
    }
    if (uckey) {
      fetch(`https://newapi.clinx.work/api/oauth/nd99u?code=${encodeURIComponent(uckey)}`)
        .then(res => res.json())
        .then(data => {
          if (data.success && data.data) {
            saveUserInfo(data.data)
            window.location.replace('/')
          } else {
            alert('登录失败: ' + (data.message || '未知错误'))
            window.location.replace('/login')
          }
        })
        .catch(() => {
          alert('验证请求失败')
          window.location.replace('/login')
        })
    } else {
      alert('未获取到uckey参数')
      window.location.replace('/login')
    }
  }, [])

  return <div>正在验证登录...</div>
}

export const Route = createFileRoute('/99u-callback')({
  component: RouteComponent,
}) 