// Mock chrome.storage API (runs before test environment)
const storage: Record<string, any> = {}

;(global as any).chrome = {
  storage: {
    local: {
      get: jest.fn(async (key: string) => {
        if (typeof key === "string") {
          return { [key]: storage[key] }
        }
        return storage
      }),
      set: jest.fn(async (items: Record<string, any>) => {
        Object.assign(storage, items)
      }),
      remove: jest.fn(async (key: string) => {
        delete storage[key]
      }),
    },
  },
  runtime: {
    getURL: jest.fn((path: string) => `chrome-extension://test-id/${path}`),
  },
  tabs: {
    create: jest.fn(),
  },
  sidePanel: {
    open: jest.fn(),
  },
}

// Mock crypto.randomUUID
Object.defineProperty(global, "crypto", {
  value: {
    randomUUID: () => "test-uuid-1234",
  },
})
