/** @type {import('ts-jest').JestConfigWithTsJest} */
module.exports = {
  testEnvironment: "jsdom",
  transform: {
    "^.+\\.tsx?$": [
      "ts-jest",
      {
        tsconfig: "tsconfig.test.json",
      },
    ],
  },
  moduleNameMapper: {
    "^~lib/(.*)$": "<rootDir>/src/lib/$1",
    "^~store/(.*)$": "<rootDir>/src/store/$1",
    "^~components/(.*)$": "<rootDir>/src/components/$1",
    "^~src/(.*)$": "<rootDir>/src/$1",
    "\\.css$": "<rootDir>/tests/__mocks__/styleMock.js",
  },
  setupFiles: ["<rootDir>/tests/setup.ts"],
  setupFilesAfterEnv: ["<rootDir>/tests/setupAfterEnv.ts"],
  testMatch: ["<rootDir>/tests/**/*.test.ts", "<rootDir>/tests/**/*.test.tsx"],
}
