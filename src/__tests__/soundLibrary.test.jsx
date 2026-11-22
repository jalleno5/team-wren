import { describe, it } from 'vitest'

describe("Sound library window", () => {
  describe("Sound selection", () => {
    it.todo("Sound is added to beat when selected")
    it.todo("Sound is removed from beat when unselected")
    it.todo("No more than 4 sounds can be added to a beat, error dialogue appears")
    it.todo("Sounds change color when added")
    it.todo("Sounds change color when removed")
    it.todo("Hitting generate with no sounds produces error dialogue")
  })

  describe("Sound management and moderation", () => {
    it.todo("Publicizing sounds works")
    it.todo("Unpublicizing sounds works")
    it.todo("Other users' public sounds can not be deleted")
    it.todo("My public sounds can be deleted")
    it.todo("My private sounds can be deleted")
    it.todo("Flagging works visually")
    it.todo("I can see sounds I have made that have been flagged and taken down back to private")
    it.todo("My private sounds can be renamed")
    it.todo("My public sounds can be renamed")
    it.todo("Other public sounds can not be renamed")
  })

  describe("Library tabs and navigation", () => {
    it.todo("Toggle to public page works")
    it.todo("Toggle to private page works")
    it.todo("Preferences button moves to second screen")
    it.todo("Clicking '2' moves to second screen")
  })
})
