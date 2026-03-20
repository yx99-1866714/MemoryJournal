import { create } from "zustand"

import { login, logout, register, restoreSession } from "~lib/auth"
import type { User } from "~lib/types"

interface AuthStore {
  user: User | null
  loading: boolean
  error: string | null

  init: () => Promise<void>
  login: (email: string, password: string) => Promise<void>
  register: (email: string, name: string, password: string) => Promise<void>
  logout: () => Promise<void>
  clearError: () => void
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  loading: true,
  error: null,

  init: async () => {
    set({ loading: true, error: null })
    try {
      const user = await restoreSession()
      set({ user, loading: false })
    } catch {
      set({ user: null, loading: false })
    }
  },

  login: async (email, password) => {
    set({ loading: true, error: null })
    try {
      const user = await login(email, password)
      set({ user, loading: false })
    } catch (err: any) {
      set({ loading: false, error: err.message || "Login failed" })
    }
  },

  register: async (email, name, password) => {
    set({ loading: true, error: null })
    try {
      const user = await register(email, name, password)
      set({ user, loading: false })
    } catch (err: any) {
      set({ loading: false, error: err.message || "Registration failed" })
    }
  },

  logout: async () => {
    await logout()
    set({ user: null, loading: false, error: null })
  },

  clearError: () => set({ error: null }),
}))
