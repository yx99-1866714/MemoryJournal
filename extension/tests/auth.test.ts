/**
 * Tests for the auth library functions.
 * Mocks the API client and verifies token management via chrome.storage.
 */

jest.mock("~lib/api", () => ({
  apiRegister: jest.fn(),
  apiLogin: jest.fn(),
  apiGetMe: jest.fn(),
  apiRefreshToken: jest.fn(),
}))

import { login, logout, register, restoreSession, refreshToken, getStoredToken } from "~lib/auth"
import { apiRegister, apiLogin, apiGetMe, apiRefreshToken } from "~lib/api"

const mockUser = { id: "u-1", email: "test@test.com", name: "Test" }

describe("auth lib", () => {
  beforeEach(() => {
    jest.clearAllMocks()
    // Clear chrome.storage mock
    ;(chrome.storage.local.get as jest.Mock).mockImplementation(async (key: string) => ({}))
    ;(chrome.storage.local.set as jest.Mock).mockImplementation(async () => {})
    ;(chrome.storage.local.remove as jest.Mock).mockImplementation(async () => {})
  })

  describe("register", () => {
    it("calls apiRegister, stores token, and returns user", async () => {
      ;(apiRegister as jest.Mock).mockResolvedValueOnce({ access_token: "tok-123", token_type: "bearer" })
      ;(apiGetMe as jest.Mock).mockResolvedValueOnce(mockUser)

      const user = await register("test@test.com", "Test", "pass")

      expect(apiRegister).toHaveBeenCalledWith("test@test.com", "Test", "pass")
      expect(chrome.storage.local.set).toHaveBeenCalledWith({ token: "tok-123" })
      expect(apiGetMe).toHaveBeenCalled()
      expect(user).toEqual(mockUser)
    })
  })

  describe("login", () => {
    it("calls apiLogin, stores token, and returns user", async () => {
      ;(apiLogin as jest.Mock).mockResolvedValueOnce({ access_token: "tok-456", token_type: "bearer" })
      ;(apiGetMe as jest.Mock).mockResolvedValueOnce(mockUser)

      const user = await login("test@test.com", "pass")

      expect(apiLogin).toHaveBeenCalledWith("test@test.com", "pass")
      expect(chrome.storage.local.set).toHaveBeenCalledWith({ token: "tok-456" })
      expect(user).toEqual(mockUser)
    })
  })

  describe("logout", () => {
    it("removes token from chrome.storage", async () => {
      await logout()
      expect(chrome.storage.local.remove).toHaveBeenCalledWith("token")
    })
  })

  describe("restoreSession", () => {
    it("returns user when valid token exists", async () => {
      ;(chrome.storage.local.get as jest.Mock).mockResolvedValueOnce({ token: "valid-tok" })
      ;(apiGetMe as jest.Mock).mockResolvedValueOnce(mockUser)

      const user = await restoreSession()
      expect(user).toEqual(mockUser)
    })

    it("returns null when no token stored", async () => {
      ;(chrome.storage.local.get as jest.Mock).mockResolvedValueOnce({})
      const user = await restoreSession()
      expect(user).toBeNull()
    })

    it("clears token and returns null when apiGetMe fails", async () => {
      ;(chrome.storage.local.get as jest.Mock).mockResolvedValueOnce({ token: "expired-tok" })
      ;(apiGetMe as jest.Mock).mockRejectedValueOnce(new Error("Invalid token"))

      const user = await restoreSession()
      expect(user).toBeNull()
      expect(chrome.storage.local.remove).toHaveBeenCalledWith("token")
    })
  })

  describe("refreshToken", () => {
    it("stores new token on success", async () => {
      ;(apiRefreshToken as jest.Mock).mockResolvedValueOnce({ access_token: "new-tok", token_type: "bearer" })

      await refreshToken()
      expect(chrome.storage.local.set).toHaveBeenCalledWith({ token: "new-tok" })
    })

    it("clears token on failure", async () => {
      ;(apiRefreshToken as jest.Mock).mockRejectedValueOnce(new Error("expired"))

      await refreshToken()
      expect(chrome.storage.local.remove).toHaveBeenCalledWith("token")
    })
  })

  describe("getStoredToken", () => {
    it("returns token when present", async () => {
      ;(chrome.storage.local.get as jest.Mock).mockResolvedValueOnce({ token: "my-token" })
      const token = await getStoredToken()
      expect(token).toBe("my-token")
    })

    it("returns null when no token", async () => {
      ;(chrome.storage.local.get as jest.Mock).mockResolvedValueOnce({})
      const token = await getStoredToken()
      expect(token).toBeNull()
    })
  })
})
