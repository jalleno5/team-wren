import { beforeEach, describe, expect, it } from 'vitest'
import { createMockApi } from '../../mock-server/routes.js'

// These call the mock API's handlers directly, so no server needs to be running
let api

beforeEach(() => {
  api = createMockApi()
})

const get = (path, query) => api({ method: 'GET', path, query })
const post = (path, body) => api({ method: 'POST', path, body })
const patch = (path, body) => api({ method: 'PATCH', path, body })
const del = (path) => api({ method: 'DELETE', path })

describe("Mock API", () => {
  it("says it's running", () => {
    expect(get('/api/health')).toEqual({ status: 200, body: { status: 'ok' } })
  })

  it("returns 404 for endpoints that don't exist", () => {
    expect(get('/api/nope').status).toBe(404)
  })

  describe("Profile", () => {
    it("returns the signed-in user's profile", () => {
      const { status, body } = get('/api/profile')

      expect(status).toBe(200)
      expect(body).toMatchObject({ id: 'user-1', username: 'demo_user' })
    })

    it("updates the username", () => {
      patch('/api/profile', { username: 'new_name' })

      expect(get('/api/profile').body.username).toBe('new_name')
    })

    it("rejects an empty username", () => {
      expect(patch('/api/profile', { username: '  ' }).status).toBe(400)
    })
  })

  describe("Sounds", () => {
    it("lists only my sounds by default", () => {
      const { body } = get('/api/sounds')

      expect(body.length).toBeGreaterThan(0)
      expect(body.every((sound) => sound.user_id === 'user-1')).toBe(true)
    })

    it("lists only public sounds with scope=public", () => {
      const { body } = get('/api/sounds', { scope: 'public' })

      expect(body.every((sound) => sound.visibility === 'public')).toBe(true)
    })

    it("creates a new private sound", () => {
      const { status, body } = post('/api/sounds', { title: 'Door slam' })

      expect(status).toBe(201)
      expect(body).toMatchObject({ title: 'Door slam', visibility: 'private', user_id: 'user-1' })
      expect(get('/api/sounds').body).toContainEqual(body)
    })

    it("renames my sound and makes it public", () => {
      const { body } = patch('/api/sounds/sound-1', { title: 'Tin kick', visibility: 'public' })

      expect(body).toMatchObject({ title: 'Tin kick', visibility: 'public' })
    })

    it("won't let me rename or delete someone else's sound", () => {
      expect(patch('/api/sounds/sound-4', { title: 'Mine now' }).status).toBe(403)
      expect(del('/api/sounds/sound-4').status).toBe(403)
    })

    it("deletes my sound", () => {
      expect(del('/api/sounds/sound-1').status).toBe(204)
      expect(get('/api/sounds').body.map((sound) => sound.id)).not.toContain('sound-1')
    })

    it("reports a public sound", () => {
      const { status, body } = post('/api/sounds/sound-4/reports', { description: 'Too loud' })

      expect(status).toBe(201)
      expect(body).toMatchObject({ sound_id: 'sound-4', reporter_id: 'user-1', description: 'Too loud' })
    })
  })

  describe("Classification", () => {
    it("returns the top 3 labels for a sound", () => {
      const { status, body } = post('/api/classify', { sound_id: 'sound-1' })

      expect(status).toBe(200)
      expect(body.labels).toHaveLength(3)
      expect(body.labels[0]).toEqual({ label: expect.any(String), score: expect.any(Number) })
    })

    it("gives the same result for the same sound", () => {
      expect(post('/api/classify', { sound_id: 'sound-2' }))
        .toEqual(post('/api/classify', { sound_id: 'sound-2' }))
    })

    it("returns 404 for an unknown sound", () => {
      expect(post('/api/classify', { sound_id: 'nope' }).status).toBe(404)
    })
  })

  describe("Beats", () => {
    const newBeat = { title: 'Test beat', speed: 120, genre: 'jazz', sound_ids: ['sound-1', 'sound-4'] }

    it("queues a beat, then shows it as completed", () => {
      const created = post('/api/beats', newBeat)
      expect(created).toEqual({ status: 202, body: { id: expect.any(String), status: 'queued' } })

      const firstCheck = get(`/api/beats/${created.body.id}`)
      expect(firstCheck.body.status).toBe('queued')

      const secondCheck = get(`/api/beats/${created.body.id}`)
      expect(secondCheck.body).toMatchObject({ status: 'completed', audio_url: expect.any(String) })
    })

    it("needs between 1 and 4 sounds", () => {
      expect(post('/api/beats', { ...newBeat, sound_ids: [] }).status).toBe(400)
      expect(post('/api/beats', {
        ...newBeat,
        sound_ids: ['sound-1', 'sound-2', 'sound-3', 'sound-4', 'sound-5'],
      }).status).toBe(400)
    })

    it("needs a speed from 60 to 200", () => {
      expect(post('/api/beats', { ...newBeat, speed: 30 }).status).toBe(400)
      expect(post('/api/beats', { ...newBeat, speed: 250 }).status).toBe(400)
    })

    it("lists my beats", () => {
      post('/api/beats', newBeat)

      expect(get('/api/beats').body).toHaveLength(2)
    })
  })
})
