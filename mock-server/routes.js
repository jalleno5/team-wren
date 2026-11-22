import { CURRENT_USER_ID, createData } from './data.js'

const MIN_SPEED = 60
const MAX_SPEED = 200
const MAX_SOUNDS_PER_BEAT = 4
const SOUND_CATEGORIES = ['percussion', 'rhythmic', 'melodic', 'ambient', 'transition']

const reply = (status, body) => ({ status, body })
const error = (status, message) => reply(status, { error: message })

// Builds the mock API. Each call gets its own data, so tests don't affect each other.
// The returned function takes a request ({ method, path, query, body })
// and returns a response ({ status, body }).
export function createMockApi(data = createData()) {
  let nextId = 100
  const newId = (prefix) => `${prefix}-${nextId++}`

  const findSound = (id) => data.sounds.find((sound) => sound.id === id)
  const canSeeSound = (sound) => sound.user_id === CURRENT_USER_ID || sound.visibility === 'public'
  const findBeat = (id) => data.beats.find((beat) => beat.id === id)

  const routes = {
    'GET /api/health': () => reply(200, { status: 'ok' }),

    // Profile

    'GET /api/profile': () => reply(200, { ...data.profile }),

    'PATCH /api/profile': ({ body }) => {
      if (body.username !== undefined && !String(body.username).trim()) {
        return error(400, 'Username cannot be empty')
      }
      if (body.username !== undefined) data.profile.username = String(body.username).trim()
      if (body.avatar_url !== undefined) data.profile.avatar_url = body.avatar_url
      return reply(200, { ...data.profile })
    },

    // Sounds

    'GET /api/sounds': ({ query }) => {
      const scope = query.scope ?? 'mine'
      if (scope === 'mine') {
        return reply(200, data.sounds.filter((sound) => sound.user_id === CURRENT_USER_ID))
      }
      if (scope === 'public') {
        return reply(200, data.sounds.filter((sound) => sound.visibility === 'public'))
      }
      return error(400, 'scope must be "mine" or "public"')
    },

    // The real version will also upload the recording. The mock only saves the title.
    'POST /api/sounds': ({ body }) => {
      const title = String(body.title ?? '').trim()
      if (!title) return error(400, 'A sound needs a title')

      const sound = { id: newId('sound'), user_id: CURRENT_USER_ID, title, visibility: 'private' }
      data.sounds.push(sound)
      return reply(201, { ...sound })
    },

    'PATCH /api/sounds/:id': ({ params, body }) => {
      const sound = findSound(params.id)
      if (!sound || !canSeeSound(sound)) return error(404, 'Sound not found')
      if (sound.user_id !== CURRENT_USER_ID) return error(403, 'You can only edit your own sounds')

      if (body.title !== undefined && !String(body.title).trim()) {
        return error(400, 'A sound needs a title')
      }
      if (body.visibility !== undefined && !['private', 'public'].includes(body.visibility)) {
        return error(400, 'visibility must be "private" or "public"')
      }
      if (body.title !== undefined) sound.title = String(body.title).trim()
      if (body.visibility !== undefined) sound.visibility = body.visibility
      return reply(200, { ...sound })
    },

    'DELETE /api/sounds/:id': ({ params }) => {
      const sound = findSound(params.id)
      if (!sound || !canSeeSound(sound)) return error(404, 'Sound not found')
      if (sound.user_id !== CURRENT_USER_ID) return error(403, 'You can only delete your own sounds')

      data.sounds = data.sounds.filter((s) => s.id !== sound.id)
      return reply(204)
    },

    'POST /api/sounds/:id/reports': ({ params, body }) => {
      const sound = findSound(params.id)
      if (!sound || !canSeeSound(sound)) return error(404, 'Sound not found')

      const report = {
        id: newId('report'),
        sound_id: sound.id,
        reporter_id: CURRENT_USER_ID,
        description: body.description ?? null,
        created_at: new Date().toISOString(),
      }
      data.sound_reports.push(report)
      return reply(201, { ...report })
    },

    // Classification

    // Returns one generation category. The same sound always gets the same result.
    'POST /api/classify': ({ body }) => {
      const sound = findSound(body.sound_id)
      if (!sound || !canSeeSound(sound)) return error(404, 'Sound not found')

      const pick = [...sound.id].reduce((sum, char) => sum + char.charCodeAt(0), 0)
      const category = data.classifications[pick % data.classifications.length]
      return reply(200, { sound_id: sound.id, category })
    },

    // Beats

    'GET /api/beats': () => reply(200, data.beats.filter((beat) => beat.user_id === CURRENT_USER_ID)),

    // Like the real generation worker, this answers right away with a "queued" job.
    // Ask for the beat with GET /api/beats/:id to get the finished result.
    'POST /api/beats': ({ body }) => {
      const { title, speed, genre = null, sounds } = body

      if (!Array.isArray(sounds) || sounds.length === 0) {
        return error(400, 'Pick at least one sound')
      }
      if (sounds.length > MAX_SOUNDS_PER_BEAT) {
        return error(400, `A beat can use at most ${MAX_SOUNDS_PER_BEAT} sounds`)
      }
      const soundIds = sounds.map((sound) => sound?.sound_id)
      if (new Set(soundIds).size !== soundIds.length) return error(400, 'Each sound can only be used once per beat')
      if (sounds.some((sound) => !SOUND_CATEGORIES.includes(sound?.category))) {
        return error(400, `Each sound needs a category: ${SOUND_CATEGORIES.join(', ')}`)
      }
      if (soundIds.some((id) => !findSound(id) || !canSeeSound(findSound(id)))) {
        return error(400, 'One or more sounds could not be found')
      }
      if (!Number.isInteger(speed) || speed < MIN_SPEED || speed > MAX_SPEED) {
        return error(400, `speed must be a whole number from ${MIN_SPEED} to ${MAX_SPEED}`)
      }

      const beat = {
        id: newId('beat'),
        user_id: CURRENT_USER_ID,
        title: String(title ?? '').trim() || 'Untitled beat',
        speed,
        genre,
        visibility: 'private',
        sounds: sounds.map((sound) => ({ sound_id: sound.sound_id, category: sound.category })),
        status: 'queued',
        audio_url: null,
      }
      data.beats.push(beat)
      return reply(202, { id: beat.id, status: beat.status })
    },

    // A new beat shows as "queued" the first time it's checked and "completed"
    // after that, so the frontend can test both the waiting and finished states
    'GET /api/beats/:id': ({ params }) => {
      const beat = findBeat(params.id)
      if (!beat || (beat.user_id !== CURRENT_USER_ID && beat.visibility !== 'public')) {
        return error(404, 'Beat not found')
      }

      const current = { ...beat }
      if (beat.status === 'queued') {
        beat.status = 'completed'
        beat.audio_url = `/mock-audio/${beat.id}.wav`
      }
      return reply(200, current)
    },
  }

  return function handle({ method, path, query = {}, body = {} }) {
    for (const [route, handler] of Object.entries(routes)) {
      const [routeMethod, routePath] = route.split(' ')
      const params = matchPath(routePath, path)
      if (params && routeMethod === method) {
        return handler({ params, query, body: body ?? {} })
      }
    }
    return error(404, `No mock endpoint for ${method} ${path}`)
  }
}

// Checks a path like /api/sounds/sound-1 against a pattern like /api/sounds/:id.
// Returns the filled-in values ({ id: 'sound-1' }), or null if it doesn't match.
function matchPath(pattern, path) {
  const patternParts = pattern.split('/')
  const pathParts = path.replace(/\/$/, '').split('/')
  if (patternParts.length !== pathParts.length) return null

  const params = {}
  for (let i = 0; i < patternParts.length; i++) {
    if (patternParts[i].startsWith(':')) {
      params[patternParts[i].slice(1)] = decodeURIComponent(pathParts[i])
    } else if (patternParts[i] !== pathParts[i]) {
      return null
    }
  }
  return params
}
