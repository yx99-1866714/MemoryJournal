/**
 * Tests for React components: AuthForm, JournalCard.
 */
import React from "react"
import { render, screen, fireEvent } from "@testing-library/react"
import "@testing-library/jest-dom"

// ---- JournalCard Tests ----
import JournalCard from "~components/JournalCard"
import type { Journal } from "~lib/types"

const makeJournal = (overrides: Partial<Journal> = {}): Journal => ({
  id: "j-1",
  user_id: "u-1",
  title: "My Test Journal",
  raw_text: "This is a test journal entry with some content.",
  status: "submitted",
  word_count: 9,
  mood_label: "😊",
  source_surface: "fullpage",
  created_at: "2026-03-19T12:00:00Z",
  updated_at: "2026-03-19T12:00:00Z",
  submitted_at: "2026-03-19T12:00:00Z",
  ...overrides,
})

describe("JournalCard", () => {
  it("renders journal title", () => {
    render(<JournalCard journal={makeJournal()} />)
    expect(screen.getByText("My Test Journal")).toBeInTheDocument()
  })

  it("shows 'Untitled Entry' when title is null", () => {
    render(<JournalCard journal={makeJournal({ title: null })} />)
    expect(screen.getByText("Untitled Entry")).toBeInTheDocument()
  })

  it("renders status badge", () => {
    render(<JournalCard journal={makeJournal({ status: "draft" })} />)
    expect(screen.getByText("draft")).toBeInTheDocument()
  })

  it("renders mood emoji", () => {
    render(<JournalCard journal={makeJournal({ mood_label: "😌" })} />)
    expect(screen.getByText("😌")).toBeInTheDocument()
  })

  it("does not render mood when mood_label is null", () => {
    const { container } = render(<JournalCard journal={makeJournal({ mood_label: null })} />)
    expect(container.querySelector(".text-lg")).not.toBeInTheDocument()
  })

  it("renders word count", () => {
    render(<JournalCard journal={makeJournal({ word_count: 42 })} />)
    expect(screen.getByText("42 words")).toBeInTheDocument()
  })

  it("truncates long text to 150 chars + ellipsis", () => {
    const longText = "A".repeat(200)
    render(<JournalCard journal={makeJournal({ raw_text: longText })} />)
    const preview = screen.getByText(/^A+\.\.\./)
    expect(preview.textContent!.length).toBeLessThanOrEqual(154) // 150 + "..."
  })

  it("calls onClick when clicked", () => {
    const onClick = jest.fn()
    render(<JournalCard journal={makeJournal()} onClick={onClick} />)
    fireEvent.click(screen.getByText("My Test Journal"))
    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it("renders all status color variants", () => {
    const statuses = ["draft", "submitted", "processed", "failed"] as const
    for (const status of statuses) {
      const { unmount } = render(<JournalCard journal={makeJournal({ status })} />)
      expect(screen.getByText(status)).toBeInTheDocument()
      unmount()
    }
  })
})
