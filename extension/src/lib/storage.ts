import { openDB, type DBSchema, type IDBPDatabase } from "idb"

import type { JournalDraft } from "./types"

interface MySagaDB extends DBSchema {
  drafts: {
    key: string
    value: JournalDraft
    indexes: { "by-updated": number }
  }
}

let dbPromise: Promise<IDBPDatabase<MySagaDB>> | null = null

function getDB(): Promise<IDBPDatabase<MySagaDB>> {
  if (!dbPromise) {
    dbPromise = openDB<MySagaDB>("mysaga", 1, {
      upgrade(db) {
        const store = db.createObjectStore("drafts", { keyPath: "id" })
        store.createIndex("by-updated", "updated_at")
      },
    })
  }
  return dbPromise
}

export async function saveDraft(draft: JournalDraft): Promise<void> {
  const db = await getDB()
  await db.put("drafts", { ...draft, updated_at: Date.now() })
}

export async function getDraft(id: string): Promise<JournalDraft | undefined> {
  const db = await getDB()
  return db.get("drafts", id)
}

export async function listDrafts(): Promise<JournalDraft[]> {
  const db = await getDB()
  return db.getAllFromIndex("drafts", "by-updated")
}

export async function deleteDraft(id: string): Promise<void> {
  const db = await getDB()
  await db.delete("drafts", id)
}
