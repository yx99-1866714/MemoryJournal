/**
 * Tests for the auth store (Zustand).
 * Mocks the auth lib functions and verifies store state transitions.
 */
import { useAuthStore } from "~store/authStore"

// Mock the auth library
jest.mock("~lib/auth", () => ({
  login: jest.fn(),
  register: jest.fn(),
  logout: jest.fn(),
  restoreSession: jest.fn(),
}))

import { login, register, logout, restoreSession } from "~lib/auth"

const mockedLogin = login as jest.MockedFunction<typeof login>
const mockedRegister = register as jest.MockedFunction<typeof register>
const mockedLogout = logout as jest.MockedFunction<typeof logout>
const mockedRestoreSession = restoreSession as jest.MockedFunction<typeof restoreSession>

const testUser = { id: "user-1", email: "test@example.com", name: "Test User" }

describe("authStore", () => {
  beforeEach(() => {
    // Reset store state
    useAuthStore.setState({
      user: null,
      loading: true,
      error: null,
    })
    jest.clearAllMocks()
  })

  describe("init", () => {
    it("restores session and sets user on success", async () => {
      mockedRestoreSession.mockResolvedValueOnce(testUser)
      await useAuthStore.getState().init()

      expect(mockedRestoreSession).toHaveBeenCalled()
      expect(useAuthStore.getState().user).toEqual(testUser)
      expect(useAuthStore.getState().loading).toBe(false)
    })

    it("sets user to null when no session exists", async () => {
      mockedRestoreSession.mockResolvedValueOnce(null)
      await useAuthStore.getState().init()

      expect(useAuthStore.getState().user).toBeNull()
      expect(useAuthStore.getState().loading).toBe(false)
    })

    it("handles restoreSession failure gracefully", async () => {
      mockedRestoreSession.mockRejectedValueOnce(new Error("Network error"))
      await useAuthStore.getState().init()

      expect(useAuthStore.getState().user).toBeNull()
      expect(useAuthStore.getState().loading).toBe(false)
    })
  })

  describe("login", () => {
    it("sets user on successful login", async () => {
      mockedLogin.mockResolvedValueOnce(testUser)
      await useAuthStore.getState().login("test@example.com", "password")

      expect(mockedLogin).toHaveBeenCalledWith("test@example.com", "password")
      expect(useAuthStore.getState().user).toEqual(testUser)
      expect(useAuthStore.getState().loading).toBe(false)
      expect(useAuthStore.getState().error).toBeNull()
    })

    it("sets error on login failure", async () => {
      mockedLogin.mockRejectedValueOnce(new Error("Invalid credentials"))
      await useAuthStore.getState().login("test@example.com", "wrong")

      expect(useAuthStore.getState().user).toBeNull()
      expect(useAuthStore.getState().loading).toBe(false)
      expect(useAuthStore.getState().error).toBe("Invalid credentials")
    })

    it("sets loading state during login", async () => {
      let resolveLogin: (value: any) => void
      mockedLogin.mockImplementation(
        () => new Promise((resolve) => { resolveLogin = resolve })
      )

      const loginPromise = useAuthStore.getState().login("test@example.com", "pass")
      // loading should be true while login is in progress
      expect(useAuthStore.getState().loading).toBe(true)

      resolveLogin!(testUser)
      await loginPromise
      expect(useAuthStore.getState().loading).toBe(false)
    })
  })

  describe("register", () => {
    it("sets user on successful registration", async () => {
      mockedRegister.mockResolvedValueOnce(testUser)
      await useAuthStore.getState().register("test@example.com", "Test User", "password")

      expect(mockedRegister).toHaveBeenCalledWith("test@example.com", "Test User", "password")
      expect(useAuthStore.getState().user).toEqual(testUser)
      expect(useAuthStore.getState().loading).toBe(false)
    })

    it("sets error on registration failure", async () => {
      mockedRegister.mockRejectedValueOnce(new Error("Email already registered"))
      await useAuthStore.getState().register("test@example.com", "User", "pass")

      expect(useAuthStore.getState().error).toBe("Email already registered")
      expect(useAuthStore.getState().user).toBeNull()
    })
  })

  describe("logout", () => {
    it("clears user state on logout", async () => {
      useAuthStore.setState({ user: testUser, loading: false })
      await useAuthStore.getState().logout()

      expect(mockedLogout).toHaveBeenCalled()
      expect(useAuthStore.getState().user).toBeNull()
      expect(useAuthStore.getState().error).toBeNull()
    })
  })

  describe("clearError", () => {
    it("clears error state", () => {
      useAuthStore.setState({ error: "some error" })
      useAuthStore.getState().clearError()
      expect(useAuthStore.getState().error).toBeNull()
    })
  })
})
