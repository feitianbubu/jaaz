import React, { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog'
import { Button } from '../ui/button'

export interface Login99uDialogProps {
  open: boolean
  onClose: () => void
  onLoginSuccess: (user: { id: number, username: string, access_token: string }) => void
}

/**
 * 99u登录对话框组件
 * 显示已登录用户信息或登录按钮
 */
export function Login99uDialog({ open, onClose, onLoginSuccess }: Login99uDialogProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [username, setUsername] = useState<string | null>(null)

  // 获取本地存储的用户信息
  useEffect(() => {
    if (open) {
      const userInfo = localStorage.getItem('jaaz_user_info')
      if (userInfo) {
        try {
          const user = JSON.parse(userInfo)
          setUsername(user.username)
        } catch (e) {
          // 忽略解析错误
          setUsername(null)
        }
      } else {
        setUsername(null)
      }
    }
  }, [open])

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>99u 登录</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <Button disabled className="flex-1">
            {username ? username : '使用99u登录'}
          </Button>
          {error && <div style={{ color: 'red' }}>{error}</div>}
        </div>
      </DialogContent>
    </Dialog>
  )
}