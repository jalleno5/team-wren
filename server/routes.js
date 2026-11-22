// endpoints and business rules
// each route is an async function that receives { params, query, body, db, user } and returns { status, body }

import { createHash, randomBytes, randomUUID } from 'node:crypto'
import { HttpError, matchPath } from './http.js'
import { admin } from './supabase.js'
import { BEAT_BUCKET } from './worker.js'

const MIN_SPEED = 60                       // slowest beat (BPM)
const MAX_SPEED = 200                      // fastest beat (BPM)
const MAX_SOUNDS_PER_BEAT = 4              // "No more than 4 sounds can be added to a beat"
const SOUND_CATEGORIES = ['percussion', 'rhythmic', 'melodic', 'ambient', 'transition']
const MAX_UPLOAD_BYTES = 10 * 1024 * 1024  // 10 MB per recording
const SIGNED_URL_SECONDS = 60 * 60         // playback links work for 1 hour
const DOWNLOAD_LINK_SECONDS = 5 * 60       // download links work for 5 minutes
const MAX_AVATAR_BYTES = 5 * 1024 * 1024   // 5 MB per profile photo

// profile photos, the bucket only accepts these types (see the avatars migration)
const AVATAR_BUCKET = 'avatars'
const AVATAR_TYPES = { 'image/jpeg': 'jpg', 'image/png': 'png', 'image/webp': 'webp', 'image/gif': 'gif' }

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

// guest tokens are saved hashed so a leaked database can't be used to grab guest beats
const hashToken = (token) => createHash('sha256').update(token).digest('hex')

// an unclaimed guest beat that matches the token, null if the token is wrong or expired
async function findGuestBeat(beatId, guestToken) {
  const { data, error } = await admin
    .from('beats')
    .select(BEAT_COLUMNS)
    .eq('id', beatId)
    .is('user_id', null)
    .eq('guest_token_hash', hashToken(guestToken))
    .gt('guest_expires_at', new Date().toISOString())
    .maybeSingle()
  failIf(error)
  return data
}

// finds a beat the person may see, members go through rls and guests need their token
// canListen is true for the owner or the guest who made it
async function findBeat({ db, user, guestToken }, beatId) {
  const { data, error } = await db.from('beats').select(BEAT_COLUMNS).eq('id', beatId).maybeSingle()
  failIf(error)
  if (data) return { row: data, canListen: Boolean(user) && data.user_id === user.id }

  if (guestToken) {
    const guestBeat = await findGuestBeat(beatId, guestToken)
    if (guestBeat) return { row: guestBeat, canListen: true }
  }
  throw new HttpError(404, 'Beat not found')  // missing, someone else's private beat, or a bad guest token
}

// adds a playable link once the beat is finished, only call after checking who is asking
async function toBeatWithAudio(row, canListen) {
  const beat = toBeatDto(row)
  if (canListen && row.output_path) {
    const { data, error } = await admin.storage.from(BEAT_BUCKET).createSignedUrl(row.output_path, SIGNED_URL_SECONDS)
    failIf(error)
    beat.audio_url = data.signedUrl
  }
  return beat
}

// links each sound to the beat, if that fails the half made beat is deleted
async function linkSounds(client, beatId, soundIds) {
  const links = soundIds.map((soundId) => ({ beat_id: beatId, sound_id: soundId }))
  const { error } = await client.from('sounds_beats').insert(links)
  if (error) {
    await client.from('beats').delete().eq('id', beatId)
    failIf(error)
  }
}

// the frontend sends the storage_path from POST /api/uploads, we save the public link to that photo
// null removes the photo
function avatarUrlFrom(value, db, user) {
  if (value === null) return null
  const path = String(value)
  if (!path.startsWith(`${user.id}/`)) throw new HttpError(400, 'avatar_url must come from POST /api/uploads')
  return db.storage.from(AVATAR_BUCKET).getPublicUrl(path).data.publicUrl
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
    if (body.avatar_url !== undefined) changes.avatar_url = avatarUrlFrom(body.avatar_url, db, user)

    // Nothing to change? Just send the profile back.
    if (Object.keys(changes).length === 0) return routes['GET /api/profile']({ db, user })

    const { data, error } = await db
      .from('users').update(changes).eq('id', user.id).select('id, username, avatar_url').single()
    failIf(error)
    return reply(200, { ...data, email: user.email })
  },

  // uploads

  // step 1 of saving a recording or profile photo: the browser asks for a one-time upload link,
  // PUTs the file straight to Supabase Storage, then calls POST /api/sounds or PATCH /api/profile (step 2)
  'POST /api/uploads': async ({ body, db, user }) => {
    requireUser(user)
    const contentType = String(body.content_type ?? '')
    const size = body.size_bytes
    const sizeOk = (max) => Number.isInteger(size) && size > 0 && size <= max

    let bucket, extension
    if (body.purpose === 'sound') {
      if (!contentType.startsWith('audio/')) throw new HttpError(400, 'Only audio files can be uploaded')
      if (!sizeOk(MAX_UPLOAD_BYTES)) throw new HttpError(400, 'Recordings must be smaller than 10 MB')
      bucket = BUCKETS.private
      extension = contentType.split('/')[1].split(';')[0] || 'webm'  // "audio/wav" -> "wav"
    } else if (body.purpose === 'avatar') {
      extension = AVATAR_TYPES[contentType]
      if (!extension) throw new HttpError(400, 'Profile photos must be JPEG, PNG, WebP or GIF')
      if (!sizeOk(MAX_AVATAR_BYTES)) throw new HttpError(400, 'Profile photos must be smaller than 5 MB')
      bucket = AVATAR_BUCKET
    } else {
      throw new HttpError(400, 'purpose must be "sound" or "avatar"')
    }

    // the storage policies require the first folder to be the user's id
    const path = `${user.id}/${randomUUID()}.${extension}`

    const { data, error } = await db.storage.from(bucket).createSignedUploadUrl(path)
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

  // members and guests can both make beats, guests get a guest_token back to poll and later claim it
  'POST /api/beats': async ({ body, db, user, ip }) => {
    const soundIds = body.sound_ids
    if (!Array.isArray(soundIds) || soundIds.length === 0) throw new HttpError(400, 'Pick at least one sound')
    if (soundIds.length > MAX_SOUNDS_PER_BEAT) {
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

    // members can use their own or public sounds (rls), guests only public ones
    let soundQuery = db.from('sounds').select('id').in('id', soundIds)
    if (!user) soundQuery = soundQuery.eq('visibility', 'public')
    const { data: visible, error: findError } = await soundQuery
    // a sound id that isn't a uuid is a bad request here, not a missing page
    if (findError?.code === '22P02') throw new HttpError(400, 'One or more sounds could not be found')
    failIf(findError)
    if (visible.length !== soundIds.length) throw new HttpError(400, 'One or more sounds could not be found')

    const fields = { title: String(body.title ?? '').trim() || 'Untitled beat', speed: body.speed, genre }

    if (user) {
      // status starts as 'queued' from the column default, the worker picks it up from there
      const { data: beat, error } = await db
        .from('beats').insert({ user_id: user.id, ...fields }).select('id, status').single()
      failIf(error)
      await linkSounds(db, beat.id, soundIds)
      // 202 = "accepted, still working on it"
      return reply(202, { id: beat.id, status: beat.status })
    }

    // guests: limit how many beats one ip can make in the last hour
    const hourAgo = new Date(Date.now() - 60 * 60 * 1000).toISOString()
    const { count, error: countError } = await admin
      .from('beats').select('id', { count: 'exact', head: true }).eq('guest_ip', ip).gte('created_at', hourAgo)
    failIf(countError)
    if (count >= GUEST_GENERATION_LIMIT_PER_HOUR) {
      throw new HttpError(429, `Guests can make ${GUEST_GENERATION_LIMIT_PER_HOUR} beats an hour. Sign in to make more.`)
    }

    // guest beats have no owner so the server makes them with the secret key
    const guestToken = randomBytes(32).toString('base64url')
    const { data: beat, error } = await admin
      .from('beats')
      .insert({
        user_id: null,
        ...fields,
        guest_token_hash: hashToken(guestToken),
        guest_expires_at: new Date(Date.now() + GUEST_JOB_TTL_MS).toISOString(),
        guest_ip: ip,
      })
      .select('id, status')
      .single()
    failIf(error)
    await linkSounds(admin, beat.id, soundIds)
    return reply(202, { id: beat.id, status: beat.status, guest_token: guestToken })
  },

  // the frontend asks this once a second until the status says "completed" or "failed"
  // guests send X-Guest-Job-Token instead of signing in
  'GET /api/beats/:id': async ({ params, db, user, guestToken }) => {
    const { row, canListen } = await findBeat({ db, user, guestToken }, params.id)
    return reply(200, await toBeatWithAudio(row, canListen))
  },

  // a guest made a beat then signed in, move the beat to their account
  // needs both the login and the guest token, calling it again after it worked just returns the beat
  'POST /api/beats/:id/claim': async ({ params, db, user, guestToken }) => {
    requireUser(user)
    if (!guestToken) throw new HttpError(400, 'Missing X-Guest-Job-Token header')

    // already yours (a retry), just send it back
    const { data: owned, error } = await db
      .from('beats').select(BEAT_COLUMNS).eq('id', params.id).eq('user_id', user.id).maybeSingle()
    failIf(error)
    if (owned) return reply(200, await toBeatWithAudio(owned, true))

    // 403 not 404 so the frontend shows this message instead of "not built yet"
    const guestBeat = await findGuestBeat(params.id, guestToken)
    if (!guestBeat) throw new HttpError(403, 'This guest beat has expired or was already saved')

    // only take it if it still has no owner so two tabs can't both claim it
    const { data: claimed, error: claimError } = await admin
      .from('beats')
      .update({ user_id: user.id, guest_token_hash: null, guest_expires_at: null })
      .eq('id', guestBeat.id)
      .is('user_id', null)
      .select(BEAT_COLUMNS)
      .maybeSingle()
    failIf(claimError)
    if (!claimed) throw new HttpError(409, 'This beat was already saved to another account')
    return reply(200, await toBeatWithAudio(claimed, true))
  },

  // short link that downloads the finished file, only for the owner (guests must sign in and claim first)
  'GET /api/beats/:id/download': async ({ params, db, user }) => {
    requireUser(user)
    const { data, error } = await db
      .from('beats').select('id, title, output_path').eq('id', params.id).eq('user_id', user.id).maybeSingle()
    failIf(error)
    // 403 not 404 so the frontend shows this message instead of "not built yet"
    if (!data) throw new HttpError(403, 'You can only download your own beats')
    if (!data.output_path) throw new HttpError(409, 'This beat is not finished yet')

    // download makes the browser save the file instead of playing it
    const { data: signed, error: signError } = await admin.storage
      .from(BEAT_BUCKET)
      .createSignedUrl(data.output_path, DOWNLOAD_LINK_SECONDS, { download: `${data.title || 'beat'}.wav` })
    failIf(signError)
    return reply(200, { url: signed.signedUrl })
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
