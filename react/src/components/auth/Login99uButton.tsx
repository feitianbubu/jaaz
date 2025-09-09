import React from 'react'
import { Button } from '@/components/ui/button'
import { start99uLogin } from '@/api/auth-99u'

export interface Login99uButtonProps {
  className?: string
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link'
}

/**
 * 99u登录按钮组件
 * 独立的99u登录入口，不修改原有UserMenu逻辑
 */
export function Login99uButton({ className, variant = 'outline' }: Login99uButtonProps) {
  const handle99uLogin = () => {
    start99uLogin()
  }

  return (
    <Button 
      variant={variant}
      onClick={handle99uLogin}
    >
      99U登录
    </Button>
  )
}