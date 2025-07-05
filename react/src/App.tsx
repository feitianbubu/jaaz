// import InstallComfyUIDialog from '@/components/comfyui/InstallComfyUIDialog'
import UpdateNotificationDialog from '@/components/common/UpdateNotificationDialog'
import SettingsDialog from '@/components/settings/dialog'
import { LoginDialog } from '@/components/auth/LoginDialog'
import { Login99uDialog } from '@/components/auth/Login99uDialog'
import { ThemeProvider } from '@/components/theme/ThemeProvider'
import { ConfigsProvider } from '@/contexts/configs'
import { AuthProvider } from '@/contexts/AuthContext'
import { useTheme } from '@/hooks/use-theme'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createRouter, RouterProvider } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { Toaster } from 'sonner'
import { routeTree } from './route-tree.gen'

import '@/assets/style/App.css'
import '@/i18n'

const router = createRouter({ routeTree })

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}

const queryClient = new QueryClient()

function App() {
  const { theme } = useTheme()
  const [showLogin99u, setShowLogin99u] = useState(false)
  const buildTag = import.meta.env.VITE_BUILD_TAG

  // Auto-start ComfyUI on app startup
  useEffect(() => {
    const autoStartComfyUI = async () => {
      try {
        // Check if ComfyUI is installed
        const isInstalled = await window.electronAPI?.checkComfyUIInstalled()
        if (!isInstalled) {
          console.log('ComfyUI is not installed, skipping auto-start')
          return
        }

        // Start ComfyUI process
        console.log('Auto-starting ComfyUI...')
        const result = await window.electronAPI?.startComfyUIProcess()

        if (result?.success) {
          console.log('ComfyUI auto-started successfully:', result.message)
        } else {
          console.log('Failed to auto-start ComfyUI:', result?.message)
        }
      } catch (error) {
        console.error('Error during ComfyUI auto-start:', error)
      }
    }

    // Only run if electronAPI is available (in Electron environment)
    if (window.electronAPI) {
      autoStartComfyUI()
    }
  }, [])

  return (
    <ThemeProvider defaultTheme={theme} storageKey="vite-ui-theme">
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <ConfigsProvider>
            <div className="app-container">
              <RouterProvider router={router} />

              {/* Install ComfyUI Dialog */}
              {/* <InstallComfyUIDialog /> */}

              {/* Update Notification Dialog */}
              <UpdateNotificationDialog />

              {/* Settings Dialog */}
              <SettingsDialog />

              {/* Login Dialog */}
              <LoginDialog />

              {/* 99u Login Dialog */}
              <Login99uDialog open={showLogin99u} onClose={() => setShowLogin99u(false)} onLoginSuccess={() => setShowLogin99u(false)} />

              {/* Build version tag at bottom right */}
              {buildTag && (
                <div style={{ position: 'fixed', right: 12, bottom: 8, fontSize: 12, color: '#888', zIndex: 9999 }}>
                  Build: {buildTag}
                </div>
              )}
            </div>
          </ConfigsProvider>
        </AuthProvider>
      </QueryClientProvider>
      <Toaster position="bottom-center" richColors />
    </ThemeProvider>
  )
}

export default App
