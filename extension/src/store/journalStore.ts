import { create } from "zustand"

import { apiCreateJournal, apiDeleteJournal, apiGetJournal, apiGetJournals, apiUpdateJournal } from "~lib/api"
import type { Journal } from "~lib/types"

interface JournalStore {
  journals: Journal[]
  currentJournal: Journal | null
  total: number
  loading: boolean
  error: string | null

  fetchJournals: (limit?: number, offset?: number) => Promise<void>
  fetchJournal: (id: string) => Promise<void>
  createJournal: (data: {
    title?: string
    content: string
    submit?: boolean
    source_surface?: string
    mood_label?: string
  }) => Promise<Journal>
  updateJournal: (id: string, data: {
    title?: string
    content?: string
    submit?: boolean
    mood_label?: string
  }) => Promise<void>
  deleteJournal: (id: string) => Promise<void>
  clearCurrent: () => void
  clearError: () => void
}

export const useJournalStore = create<JournalStore>((set, get) => ({
  journals: [],
  currentJournal: null,
  total: 0,
  loading: false,
  error: null,

  fetchJournals: async (limit = 50, offset = 0) => {
    set({ loading: true, error: null })
    try {
      const res = await apiGetJournals(limit, offset)
      set({ journals: res.journals, total: res.total, loading: false })
    } catch (err: any) {
      set({ loading: false, error: err.message })
    }
  },

  fetchJournal: async (id) => {
    set({ loading: true, error: null })
    try {
      const journal = await apiGetJournal(id)
      set({ currentJournal: journal, loading: false })
    } catch (err: any) {
      set({ loading: false, error: err.message })
    }
  },

  createJournal: async (data) => {
    set({ loading: true, error: null })
    try {
      const journal = await apiCreateJournal(data)
      set((state) => ({
        journals: [journal, ...state.journals],
        total: state.total + 1,
        loading: false,
      }))
      return journal
    } catch (err: any) {
      set({ loading: false, error: err.message })
      throw err
    }
  },

  updateJournal: async (id, data) => {
    set({ loading: true, error: null })
    try {
      const updated = await apiUpdateJournal(id, data)
      set((state) => ({
        journals: state.journals.map((j) => (j.id === id ? updated : j)),
        currentJournal: state.currentJournal?.id === id ? updated : state.currentJournal,
        loading: false,
      }))
    } catch (err: any) {
      set({ loading: false, error: err.message })
    }
  },

  deleteJournal: async (id) => {
    set({ loading: true, error: null })
    try {
      await apiDeleteJournal(id)
      set((state) => ({
        journals: state.journals.filter((j) => j.id !== id),
        total: state.total - 1,
        currentJournal: state.currentJournal?.id === id ? null : state.currentJournal,
        loading: false,
      }))
    } catch (err: any) {
      set({ loading: false, error: err.message })
    }
  },

  clearCurrent: () => set({ currentJournal: null }),
  clearError: () => set({ error: null }),
}))
