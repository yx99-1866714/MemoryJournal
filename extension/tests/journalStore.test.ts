/**
 * Tests for the journal store (Zustand).
 * Mocks the API client and verifies store state transitions.
 */
import { useJournalStore } from "~store/journalStore"
import type { Journal, JournalListResponse } from "~lib/types"

jest.mock("~lib/api", () => ({
  apiGetJournals: jest.fn(),
  apiGetJournal: jest.fn(),
  apiCreateJournal: jest.fn(),
  apiUpdateJournal: jest.fn(),
  apiDeleteJournal: jest.fn(),
}))

import {
  apiGetJournals,
  apiGetJournal,
  apiCreateJournal,
  apiUpdateJournal,
  apiDeleteJournal,
} from "~lib/api"

const makeJournal = (overrides: Partial<Journal> = {}): Journal => ({
  id: "j-1",
  user_id: "u-1",
  title: "Test Journal",
  raw_text: "Hello world",
  status: "submitted",
  word_count: 2,
  mood_label: "😊",
  source_surface: "fullpage",
  created_at: "2026-03-19T00:00:00Z",
  updated_at: "2026-03-19T00:00:00Z",
  submitted_at: "2026-03-19T00:00:00Z",
  ...overrides,
})

describe("journalStore", () => {
  beforeEach(() => {
    useJournalStore.setState({
      journals: [],
      currentJournal: null,
      total: 0,
      loading: false,
      error: null,
    })
    jest.clearAllMocks()
  })

  describe("fetchJournals", () => {
    it("fetches and sets journals list", async () => {
      const journals = [makeJournal({ id: "j-1" }), makeJournal({ id: "j-2" })]
      ;(apiGetJournals as jest.Mock).mockResolvedValueOnce({ journals, total: 2 })

      await useJournalStore.getState().fetchJournals(50, 0)

      expect(apiGetJournals).toHaveBeenCalledWith(50, 0)
      expect(useJournalStore.getState().journals).toEqual(journals)
      expect(useJournalStore.getState().total).toBe(2)
      expect(useJournalStore.getState().loading).toBe(false)
    })

    it("sets error on fetch failure", async () => {
      ;(apiGetJournals as jest.Mock).mockRejectedValueOnce(new Error("Network error"))
      await useJournalStore.getState().fetchJournals()

      expect(useJournalStore.getState().error).toBe("Network error")
      expect(useJournalStore.getState().loading).toBe(false)
    })
  })

  describe("fetchJournal", () => {
    it("fetches and sets a single journal", async () => {
      const journal = makeJournal()
      ;(apiGetJournal as jest.Mock).mockResolvedValueOnce(journal)

      await useJournalStore.getState().fetchJournal("j-1")

      expect(apiGetJournal).toHaveBeenCalledWith("j-1")
      expect(useJournalStore.getState().currentJournal).toEqual(journal)
    })

    it("sets error when journal not found", async () => {
      ;(apiGetJournal as jest.Mock).mockRejectedValueOnce(new Error("Not found"))
      await useJournalStore.getState().fetchJournal("nonexistent")

      expect(useJournalStore.getState().error).toBe("Not found")
    })
  })

  describe("createJournal", () => {
    it("creates journal and prepends to list", async () => {
      const existing = makeJournal({ id: "j-old" })
      useJournalStore.setState({ journals: [existing], total: 1 })

      const newJournal = makeJournal({ id: "j-new", title: "New" })
      ;(apiCreateJournal as jest.Mock).mockResolvedValueOnce(newJournal)

      const result = await useJournalStore.getState().createJournal({
        content: "Hello",
        submit: true,
      })

      expect(result).toEqual(newJournal)
      expect(useJournalStore.getState().journals[0].id).toBe("j-new")
      expect(useJournalStore.getState().total).toBe(2)
    })

    it("throws and sets error on create failure", async () => {
      ;(apiCreateJournal as jest.Mock).mockRejectedValueOnce(new Error("Server error"))

      await expect(
        useJournalStore.getState().createJournal({ content: "test" })
      ).rejects.toThrow("Server error")

      expect(useJournalStore.getState().error).toBe("Server error")
    })
  })

  describe("updateJournal", () => {
    it("updates journal in list and currentJournal", async () => {
      const original = makeJournal({ id: "j-1", title: "Old" })
      useJournalStore.setState({
        journals: [original],
        currentJournal: original,
        total: 1,
      })

      const updated = makeJournal({ id: "j-1", title: "Updated" })
      ;(apiUpdateJournal as jest.Mock).mockResolvedValueOnce(updated)

      await useJournalStore.getState().updateJournal("j-1", { title: "Updated" })

      expect(useJournalStore.getState().journals[0].title).toBe("Updated")
      expect(useJournalStore.getState().currentJournal?.title).toBe("Updated")
    })

    it("does not update currentJournal if it's a different journal", async () => {
      const current = makeJournal({ id: "j-current" })
      const other = makeJournal({ id: "j-other" })
      useJournalStore.setState({
        journals: [current, other],
        currentJournal: current,
      })

      const updatedOther = makeJournal({ id: "j-other", title: "Changed" })
      ;(apiUpdateJournal as jest.Mock).mockResolvedValueOnce(updatedOther)

      await useJournalStore.getState().updateJournal("j-other", { title: "Changed" })

      expect(useJournalStore.getState().currentJournal?.id).toBe("j-current")
    })
  })

  describe("deleteJournal", () => {
    it("removes journal from list and decrements total", async () => {
      const j1 = makeJournal({ id: "j-1" })
      const j2 = makeJournal({ id: "j-2" })
      useJournalStore.setState({ journals: [j1, j2], total: 2 })

      ;(apiDeleteJournal as jest.Mock).mockResolvedValueOnce(undefined)
      await useJournalStore.getState().deleteJournal("j-1")

      expect(useJournalStore.getState().journals).toHaveLength(1)
      expect(useJournalStore.getState().journals[0].id).toBe("j-2")
      expect(useJournalStore.getState().total).toBe(1)
    })

    it("clears currentJournal if it matches deleted journal", async () => {
      const journal = makeJournal({ id: "j-1" })
      useJournalStore.setState({ journals: [journal], currentJournal: journal, total: 1 })

      ;(apiDeleteJournal as jest.Mock).mockResolvedValueOnce(undefined)
      await useJournalStore.getState().deleteJournal("j-1")

      expect(useJournalStore.getState().currentJournal).toBeNull()
    })
  })

  describe("clearCurrent / clearError", () => {
    it("clears current journal", () => {
      useJournalStore.setState({ currentJournal: makeJournal() })
      useJournalStore.getState().clearCurrent()
      expect(useJournalStore.getState().currentJournal).toBeNull()
    })

    it("clears error", () => {
      useJournalStore.setState({ error: "some error" })
      useJournalStore.getState().clearError()
      expect(useJournalStore.getState().error).toBeNull()
    })
  })
})
