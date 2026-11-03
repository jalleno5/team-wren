import { describe, it } from 'vitest'

describe("Login", () => {
  describe("Sign-in", () => {
    it.todo("Clicking login directs a user from the open page upon good credentials")
    it.todo("Clicking login raises a visible error upon bad credentials")
    it.todo("Bad request on login screen returns custom visual")
  })

  describe("Password recovery", () => {
    it.todo("\"Forgot Password\" directs to the correct screen")
    it.todo("Invalid email on \"Forgot Password\" screen produces visual error")
    it.todo("Proper email on \"Forgot Password\" screen produces visual feedback")
    it.todo("User can return to login without resetting from \"Forgot Password\" screen")
    it.todo("User can return to login after resetting password")
  })
})
