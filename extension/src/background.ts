export {}

// Background service worker
// Handles extension lifecycle events

chrome.runtime.onInstalled.addListener(() => {
  console.log("Memory Journal extension installed")
})

// Open side panel when clicking extension icon (optional behavior)
chrome.action.onClicked.addListener(async (tab) => {
  // Default behavior already opens popup.
  // If no popup, this would open the side panel:
  // await chrome.sidePanel.open({ windowId: tab.windowId })
})
