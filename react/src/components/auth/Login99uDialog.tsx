import React, { useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog'
import { Button } from '../ui/button'

export function Login99uDialog({ open, onClose, onLoginSuccess }: {
  open: boolean
  onClose: () => void
  onLoginSuccess: (user: { id: number, username: string, access_token: string }) => void
}) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [username, setUsername] = useState<string | null>(null)

  React.useEffect(() => {
    const userInfo = localStorage.getItem('jaaz_user_info')
    if (userInfo) {
      try {
        const user = JSON.parse(userInfo)
        setUsername(user.username)
      } catch (e) {
        // ignore parse error
      }
    } else {
      setUsername(null)
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