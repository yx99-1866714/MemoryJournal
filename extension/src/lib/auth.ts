import { apiGetMe, apiLogin, apiRefreshToken, apiRegister } from "./api"
import type { TokenResponse, User } from "./types"

/**
 * Store the JWT token in chrome.storage.local.
 */
async function storeToken(token: string): Promise<void> {
  await chrome.storage.local.set({ token })
}

/**
 * Clear the stored token.
 */
async function clearToken(): Promise<void> {
  await chrome.storage.local.remove("token")
}

/**
 * Get the stored token.
 */
export async function getStoredToken(): Promise<string | null> {
  const result = await chrome.storage.local.get("token")
  return (result.token as string) || null
}

/**
 * Register a new user, store token, and return user info.
 */
export async function register(
  email: string,
  name: string,
  password: string
): Promise<User> {
  const tokenRes: TokenResponse = await apiRegister(email, name, password)
  await storeToken(tokenRes.access_token)
  return apiGetMe()
}

/**
 * Log in with email/password, store token, and return user info.
 */
export async function login(email: string, password: string): Promise<User> {
  const tokenRes: TokenResponse = await apiLogin(email, password)
  await storeToken(tokenRes.access_token)
  return apiGetMe()
}

/**
 * Log out by clearing the stored token.
 */
export async function logout(): Promise<void> {
  await clearToken()
}

/**
 * Try to restore session from stored token.
 */
export async function restoreSession(): Promise<User | null> {
  const token = await getStoredToken()
  if (!token) return null
  try {
    return await apiGetMe()
  } catch {
    await clearToken()
    return null
  }
}

/**
 * Refresh the JWT token.
 */
export async function refreshToken(): Promise<void> {
  try {
    const tokenRes = await apiRefreshToken()
    await storeToken(tokenRes.access_token)
  } catch {
    await clearToken()
  }
}
