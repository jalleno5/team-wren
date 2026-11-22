// endpoints and business rules
// each route is an async function that receives { params, query, body, db, user } and returns { status, body }

import { randomUUID } from 'node:crypto'
import { HttpError, matchPath } from './http.js'

const MIN_SPEED = 60                       // slowest beat (BPM)
const MAX_SPEED = 200                      // fastest beat (BPM)
const MAX_SOUNDS_PER_BEAT = 4              // "No more than 4 sounds can be added to a beat"
const SOUND_CATEGORIES = ['percussion', 'rhythmic', 'melodic', 'ambient', 'transition']
const MAX_UPLOAD_BYTES = 10 * 1024 * 1024  // 10 MB per recording
const SIGNED_URL_SECONDS = 60 * 60         // playback links work for 1 hour

// sound buckets with visibility
const BUCKETS = { private: 'sounds-private', public: 'sounds-public' }
const VISIBILITIES = ['private', 'public']
const SOURCE_TYPES = ['recorded', 'uploaded']

// reporting sounds
const REPORT_REASONS = ['Inappropriate content', 'Copyright concern', 'Spam or misleading']

// bound unauthenticated compute/storage: guest jobs expire after 1 hour and each IP may create at most 2 guest generations in a rolling hour
export const GUEST_JOB_TTL_MS = 60 * 60 * 1000
export const GUEST_GENERATION_LIMIT_PER_HOUR = 2

const reply = (status, body) => ({ status, body })

// stops the request with 401 if nobody is logged in otherwise hands back the user
function requireUser(user) {
  if (!user) throw new HttpError(401, 'Please sign in first')
  return user
}

// trims spaces off text, and rejects it if nothing is left
function cleanText(value, message) {
  const text = String(value ?? '').trim()
  if (!text) throw new HttpError(400, message)
  return text
}

// turns supabase problem reports into the right HTTP error
function failIf(error) {
  if (!error) return
  if (error.code === '42501') throw new HttpError(403, 'You are not allowed to do that') // blocked by a grant/policy
  if (error.code === '22P02') throw new HttpError(404, 'Not found')                      // the id wasn't a valid uuid
  // storage errors have an http status instead of a postgres code
  const storageStatus = Number(error.statusCode ?? error.status)
  if (storageStatus === 403) throw new HttpError(403, 'You are not allowed to do that')
  if (storageStatus === 404) throw new HttpError(404, 'File not found')
  throw error                                                                          // anything else is a bug -> 500
}

// "creator:users ( username )" = also fetch the owner's username from the users table
// and name it "creator". Supabase can do this because sounds.user_id points at users.id
const SOUND_COLUMNS = 'id, user_id, title, visibility, storage_path, created_at, creator:users ( username )'

// shapes a database row the way the frontend expects (see SoundDto in src/services.ts)
// storage_path is left out on purpose: the browser gets files through signed links instead
function toSoundDto(row) {
  return {
    id: row.id,
    user_id: row.user_id,
    title: row.title,
    visibility: row.visibility,
    creator: row.creator?.username,
    created_at: row.created_at,
  }
}

// RLS only returns sounds you're allowed to see
async function findSound(db, soundId) {
  const { data, error } = await db.from('sounds').select(SOUND_COLUMNS).eq('id', soundId).maybeSingle()
  failIf(error)
  if (!data) throw new HttpError(404, 'Sound not found')
  return data
}

// business rule: you can see other people's public sounds, but only change your own
async function findOwnSound(db, user, soundId, action) {
  const sound = await findSound(db, soundId)
  if (sound.user_id !== user.id) throw new HttpError(403, `You can only ${action} your own sounds`)
  return sound
}

// Fetch the sound/category pairs that the generation worker consumes.
const BEAT_COLUMNS =
  'id, user_id, title, speed, genre, visibility, status, error_message, output_path, duration_in_ms, created_at, sounds_beats ( sound_id, category )'

function toBeatDto(row) {
  return {
    id: row.id,
    user_id: row.user_id,
    title: row.title,
    speed: row.speed,
    genre: row.genre,
    visibility: row.visibility,
    status: row.status,
    error: row.error_message ?? undefined,
    duration_seconds: row.duration_in_ms == null ? undefined : row.duration_in_ms / 1000,
    sounds: row.sounds_beats.map((link) => ({ sound_id: link.sound_id, category: link.category })),
    created_at: row.created_at,
  }
}
// ROUTES ("METHOD /path": async function)
const routes = {
  'GET /api/health': async () => reply(200, { status: 'ok' }),

  // profile

  'GET /api/profile': async ({ db, user }) => {
    requireUser(user)
    const { data, error } = await db
      .from('users').select('id, username, avatar_url').eq('id', user.id).maybeSingle()
    failIf(error)
    if (!data) throw new HttpError(404, 'Profile not found')
    // email is hidden in public.users (our migration), so take it from the login itself
    return reply(200, { ...data, email: user.email })
  },

  'PATCH /api/profile': async ({ body, db, user }) => {
    requireUser(user)

    const changes = {}
    if (body.username !== undefined) changes.username = cleanText(body.username, 'Username cannot be empty')
    if (body.avatar_url !== undefined) changes.avatar_url = body.avatar_url

    // Nothing to change? Just send the profile back.
    if (Object.keys(changes).length === 0) return routes['GET /api/profile']({ db, user })

    const { data, error } = await db
      .from('users').update(changes).eq('id', user.id).select('id, username, avatar_url').single()
    failIf(error)
    return reply(200, { ...data, email: user.email })
  },

  // uploads

  // step 1 of saving a recording: the browser asks for a one-time upload link,
  // PUTs the file straight to Supabase Storage, then calls POST /api/sounds (step 2)
  'POST /api/uploads': async ({ body, db, user }) => {
    requireUser(user)
    // 404 makes the frontend show "not built yet" (there's no avatar bucket yet)
    if (body.purpose !== 'sound') throw new HttpError(404, 'Only sound uploads are supported right now')

    const contentType = String(body.content_type ?? '')
    if (!contentType.startsWith('audio/')) throw new HttpError(400, 'Only audio files can be uploaded')
    if (!Number.isInteger(body.size_bytes) || body.size_bytes <= 0 || body.size_bytes > MAX_UPLOAD_BYTES) {
      throw new HttpError(400, 'Recordings must be smaller than 10 MB')
    }

    // "audio/wav" -> "wav". Gavin's policies require the first folder to be the user's id.
    const extension = contentType.split('/')[1].split(';')[0] || 'webm'
    const path = `${user.id}/${randomUUID()}.${extension}`

    const { data, error } = await db.storage.from(BUCKETS.private).createSignedUploadUrl(path)
    failIf(error)
    return reply(201, {
      upload_url: data.signedUrl,
      storage_path: data.path,
      headers: { 'Content-Type': contentType },
    })
  },

  // sounds

  'GET /api/sounds': async ({ query, db, user }) => {
    const scope = query.scope ?? 'mine'
    // build the query step by step
    let request = db.from('sounds').select(SOUND_COLUMNS).order('created_at', { ascending: false })

    if (scope === 'mine') request = request.eq('user_id', requireUser(user).id)
    else if (scope === 'public') request = request.eq('visibility', 'public')  // guests may browse these
    else throw new HttpError(400, 'scope must be "mine" or "public"')

    const { data, error } = await request
    failIf(error)
    return reply(200, data.map(toSoundDto))
  },

  // step 2 of saving a recording: save the row that points at the uploaded file
  'POST /api/sounds': async ({ body, db, user }) => {
    requireUser(user)
    const title = cleanText(body.title, 'A sound needs a title')

    // only accept files in your folder, so nobody can claim someone else's upload
    const storagePath = String(body.storage_path ?? '')
    if (!storagePath.startsWith(`${user.id}/`)) {
      throw new HttpError(400, 'storage_path must come from POST /api/uploads')
    }

    const sourceType = body.source_type ?? 'recorded'
    if (!SOURCE_TYPES.includes(sourceType)) throw new HttpError(400, 'source_type must be "recorded" or "uploaded"')

    if (!Number.isInteger(body.duration_in_ms) || body.duration_in_ms <= 0) {
      throw new HttpError(400, 'duration_in_ms must be a positive whole number')
    }

    const { data, error } = await db
      .from('sounds')
      .insert({
        user_id: user.id,
        title,
        source_type: sourceType,
        duration_in_ms: body.duration_in_ms,
        storage_path: storagePath,
      })
      .select(SOUND_COLUMNS)
      .single()
    failIf(error)
    return reply(201, toSoundDto(data))
  },

  // a temporary link the audio player can use
  'GET /api/sounds/:id/playback': async ({ params, db }) => {
    const sound = await findSound(db, params.id)
    const { data, error } = await db.storage
      .from(BUCKETS[sound.visibility])
      .createSignedUrl(sound.storage_path, SIGNED_URL_SECONDS)
    failIf(error)
    return reply(200, { url: data.signedUrl, trim_start_seconds: 0 })
  },

  // rename, and/or switch between public and private
  'PATCH /api/sounds/:id': async ({ params, body, db, user }) => {
    requireUser(user)
    const sound = await findOwnSound(db, user, params.id, 'edit')
    const changes = {}

    if (body.title !== undefined) changes.title = cleanText(body.title, 'A sound needs a title')

    const newVisibility = body.visibility
    if (newVisibility !== undefined && !VISIBILITIES.includes(newVisibility)) {
      throw new HttpError(400, 'visibility must be "private" or "public"')
    }

    // changing visibility means moving the file to the other bucket too
    const moving = newVisibility !== undefined && newVisibility !== sound.visibility
    if (moving) {
      const { error } = await db.storage
        .from(BUCKETS[sound.visibility])
        .move(sound.storage_path, sound.storage_path, { destinationBucket: BUCKETS[newVisibility] })
      failIf(error)
      changes.visibility = newVisibility
    }

    if (Object.keys(changes).length === 0) return reply(200, toSoundDto(sound))

    const { data, error } = await db
      .from('sounds').update(changes).eq('id', sound.id).select(SOUND_COLUMNS).single()
    if (error && moving) {
      // the row didn't save, so move the file back to where it was
      await db.storage
        .from(BUCKETS[newVisibility])
        .move(sound.storage_path, sound.storage_path, { destinationBucket: BUCKETS[sound.visibility] })
    }
    failIf(error)
    return reply(200, toSoundDto(data))
  },

  'DELETE /api/sounds/:id': async ({ params, db, user }) => {
    requireUser(user)
    const sound = await findOwnSound(db, user, params.id, 'delete')

    // delete the row first, sounds_beats links and reports are removed with it
    const { error } = await db.from('sounds').delete().eq('id', sound.id)
    failIf(error)

    // then the audio file, the sound is already gone so a failure here only gets logged
    const { error: fileError } = await db.storage.from(BUCKETS[sound.visibility]).remove([sound.storage_path])
    if (fileError) console.error(`sound ${sound.id} was deleted but its file wasn't:`, sound.storage_path, fileError)
    return reply(204)
  },

  // flagging, Ezra's frontend sends the chosen reason as "description";
  // Gavin's table stores it in "reason" and this route translates between the two
  'POST /api/sounds/:id/reports': async ({ params, body, db, user }) => {
    requireUser(user)
    const reason = body.description
    if (!REPORT_REASONS.includes(reason)) {
      throw new HttpError(400, `Choose a reason: ${REPORT_REASONS.join(', ')}`)
    }
    await findSound(db, params.id)  // 404 if you can't see the sound

    const { data, error } = await db
      .from('sound_reports')
      .insert({ sound_id: params.id, reporter_id: user.id, reason })
      .select('id, sound_id, reason, created_at')
      .single()
    failIf(error)
    return reply(201, { id: data.id, sound_id: data.sound_id, description: data.reason, created_at: data.created_at })
  },

  // beats

  'GET /api/beats': async ({ db, user }) => {
    requireUser(user)
    const { data, error } = await db
      .from('beats').select(BEAT_COLUMNS).eq('user_id', user.id).order('created_at', { ascending: false })
    failIf(error)
    return reply(200, data.map(toBeatDto))
  },

  'POST /api/beats': async ({ body, db, user }) => {
    if (!user) {
      throw new HttpError(401, 'Sign in to generate a beat. Guest generation is coming soon.')
    }

    const sounds = body.sounds
    if (!Array.isArray(sounds) || sounds.length === 0) throw new HttpError(400, 'Pick at least one sound')
    if (sounds.length > MAX_SOUNDS_PER_BEAT) {
      throw new HttpError(400, `A beat can use at most ${MAX_SOUNDS_PER_BEAT} sounds`)
    }
    const soundIds = sounds.map((sound) => sound?.sound_id)
    if (new Set(soundIds).size !== soundIds.length) {
      throw new HttpError(400, 'Each sound can only be used once per beat')
    }
    if (sounds.some((sound) => !SOUND_CATEGORIES.includes(sound?.category))) {
      throw new HttpError(400, `Each sound needs a category: ${SOUND_CATEGORIES.join(', ')}`)
    }
    if (!Number.isInteger(body.speed) || body.speed < MIN_SPEED || body.speed > MAX_SPEED) {
      throw new HttpError(400, `speed must be a whole number from ${MIN_SPEED} to ${MAX_SPEED}`)
    }
    const genre = body.genre == null ? null : String(body.genre)

    const { data: visible, error: findError } = await db.from('sounds').select('id').in('id', soundIds)
    // a sound id that isn't a uuid is a bad request here, not a missing page
    if (findError?.code === '22P02') throw new HttpError(400, 'One or more sounds could not be found')
    failIf(findError)
    if (visible.length !== soundIds.length) throw new HttpError(400, 'One or more sounds could not be found')

    // 1. create the beat (status starts as 'queued' from the column default)
    const { data: beat, error: beatError } = await db
      .from('beats')
      .insert({ user_id: user.id, title: String(body.title ?? '').trim() || 'Untitled beat', speed: body.speed, genre })
      .select('id, status')
      .single()
    failIf(beatError)

    // 2. link each sound to it, if that fails, delete the half-made beat
    const links = sounds.map((sound) => ({ beat_id: beat.id, sound_id: sound.sound_id, category: sound.category }))
    const { error: linkError } = await db.from('sounds_beats').insert(links)
    if (linkError) {
      await db.from('beats').delete().eq('id', beat.id)
      failIf(linkError)
    }

    // 202 = "accepted, still working on it", the generation worker will update the status later
    return reply(202, { id: beat.id, status: beat.status })
  },

  // the frontend asks this once a second until the status says "completed" or "failed"
  'GET /api/beats/:id': async ({ params, db, user }) => {
    const { data, error } = await db.from('beats').select(BEAT_COLUMNS).eq('id', params.id).maybeSingle()
    failIf(error)
    if (!data) throw new HttpError(404, 'Beat not found')  // missing, or someone else's private beat
    const beat = toBeatDto(data)

    // the worker saves the file as <user id>/beats/<beat id>.wav in the private bucket
    // so only the owner can get a link for now
    if (data.output_path && data.user_id === user?.id) {
      const { data: signed, error: signError } = await db.storage
        .from(BUCKETS.private)
        .createSignedUrl(data.output_path, SIGNED_URL_SECONDS)
      failIf(signError)
      beat.audio_url = signed.signedUrl
    }
    return reply(200, beat)
  },
}

// server.js calls this to find which route handles a request
// returns { handler, params } or null if nothing matches
export function findRoute(method, path) {
  for (const [key, handler] of Object.entries(routes)) {
    const [routeMethod, pattern] = key.split(' ')
    if (routeMethod !== method) continue
    const params = matchPath(pattern, path)
    if (params) return { handler, params }
  }
  return null
}
