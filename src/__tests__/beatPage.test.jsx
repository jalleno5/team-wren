import { describe, it } from 'vitest'

describe("Beat Page", () => {
  describe("Playback and download", () => {
    it.todo("Play button works")
    it.todo("Pause button works")
    it.todo("Audio is being produced")
    it.todo("Download button works")
  })

  describe("Navigation and progress warnings", () => {
    it.todo("Go back to screen 2 provides warning of deleting progress")
    it.todo("Go back to screen 2 rejection works")
    it.todo("Go back to screen 2 acceptance works")
    it.todo("Go back to screen 1 provides warning of deleting progress")
    it.todo("Go back to screen 1 rejection works")
    it.todo("Go back to screen 1 acceptance works")
  })

  describe("Creating and regenerating beats", () => {
    it.todo("New beat button provides warning of deleting progress")
    it.todo("Regenerate button works and beat is different usually")
  })
})
