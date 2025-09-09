import { BASE_API_URL } from '../constants'
import { authenticatedFetch } from './auth'

export interface BalanceResponse {
  balance: string
}

export async function getBalance(): Promise<BalanceResponse> {
  const response = await authenticatedFetch(
    `${BASE_API_URL}/api/user/self`
  )

  if (!response.ok) {
    throw new Error(`Failed to fetch balance: ${response.status}`)
  }

    const data = await response.json()
    const balance = formatCurrency(data)
    return {balance}
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function formatCurrency(data: any): string {
    let balance = data?.balance
    if (balance) {
        return balance
    }
    balance = data?.data?.quota || 0

    // 格式化为人类易读的格式 (K, M, B)
    function formatBalance(num: number): string {
        if (num >= 1_000_000_000) {
            return (num / 1_000_000_000).toFixed(1) + 'B'
        } else if (num >= 1_000_000) {
            return (num / 1_000_000).toFixed(1) + 'M'
        } else if (num >= 1_000) {
            return (num / 1_000).toFixed(1) + 'K'
        }
        return num.toString()
    }
    return formatBalance(balance)
}