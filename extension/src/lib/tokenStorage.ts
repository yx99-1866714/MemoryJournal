/**
 * Token storage utilities — abstracts chrome.storage.local vs localStorage.
 * Extracted to avoid circular dependency between auth.ts and api.ts.
 */

// Detect whether chrome.storage is available (Chrome extension context)
const hasChromeStorage = typeof chrome !== "undefined" && chrome.storage?.local

export async function storeToken(token: string): Promise<void> {
  if (hasChromeStorage) {
    await chrome.storage.local.set({ token })
  } else {
    localStorage.setItem("token", token)
  }
}

export async function clearToken(): Promise<void> {
  if (hasChromeStorage) {
    await chrome.storage.local.remove("token")
  } else {
    localStorage.removeItem("token")
  }
}

export async function getStoredToken(): Promise<string | null> {
  if (hasChromeStorage) {
    const result = await chrome.storage.local.get("token")
    return (result.token as string) || null
  } else {
    return localStorage.getItem("token")
  }
}
