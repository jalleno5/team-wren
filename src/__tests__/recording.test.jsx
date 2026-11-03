import { describe, it } from 'vitest'

describe("Recording", () => {
  describe("Opening and dismissing the recorder", () => {
    it.todo("Record button opens recording window")
    it.todo("Recording window can be closed without recording")
    it.todo("Recording window closed by X after recording produces no sound")
    it.todo("Recording window prompts user to name recording before saving")
  })

  describe("Audio capture", () => {
    it.todo("Recording when given no signal does not begin")
    it.todo("Recording picks up sound")
  })
})
