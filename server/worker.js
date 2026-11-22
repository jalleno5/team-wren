// beat worker, finishes queued beats in the background
// the real generation (fermata + rendering with the user's sounds) isn't connected yet
// so every beat gets the same sample file, swap out makeBeatAudio when it's ready

import { readFile } from 'node:fs/promises'
import { admin } from './supabase.js'

const POLL_MS = 2000            // look for new beats every 2 seconds
const CLEANUP_MS = 60 * 1000    // look for expired guest beats every minute
export const BEAT_BUCKET = 'beats'
const PLACEHOLDER_FILE = new URL('../Pattern_Testing/Songs/Music_Gen_Songs/musicgen_output.wav', import.meta.url)

// stand in for real generation, gets the beat row (speed, genre) and gives back the finished wav
// _beat isn't used yet, the real generator will need it
async function makeBeatAudio(_beat) {
  const bytes = await readFile(PLACEHOLDER_FILE)
  return { bytes, durationInMs: wavDurationInMs(bytes) }
}

// a wav file is a list of chunks, "fmt " says how many bytes play per second and "data" holds the sound
function wavDurationInMs(bytes) {
  let offset = 12  // skip the "RIFF....WAVE" header
  let byteRate = 0
  while (offset + 8 <= bytes.length) {
    const id = bytes.toString('ascii', offset, offset + 4)
    const size = bytes.readUInt32LE(offset + 4)
    if (id === 'fmt ') byteRate = bytes.readUInt32LE(offset + 16)
    if (id === 'data' && byteRate) return Math.round((size / byteRate) * 1000)
    offset += 8 + size + (size % 2)  // chunks are padded to an even length
  }
  throw new Error('could not read the length of the wav file')
}

// finishes the oldest queued beat, returns false when there's nothing to do
async function processNextBeat() {
  const { data: next, error } = await admin
    .from('beats').select('id').eq('status', 'queued').order('created_at').limit(1).maybeSingle()
  if (error) throw error
  if (!next) return false

  // only take it if it's still queued so two workers never do the same beat
  const { data: beat, error: takeError } = await admin
    .from('beats').update({ status: 'processing' }).eq('id', next.id).eq('status', 'queued')
    .select('id, speed, genre').maybeSingle()
  if (takeError) throw takeError
  if (!beat) return true  // someone else took it, try the next one

  try {
    const { bytes, durationInMs } = await makeBeatAudio(beat)
    // the file is named after the beat not the owner, so claiming a guest beat doesn't need to move it
    const path = `${beat.id}.wav`
    const { error: uploadError } = await admin.storage
      .from(BEAT_BUCKET).upload(path, bytes, { contentType: 'audio/wav', upsert: true })
    if (uploadError) throw uploadError

    const { error: doneError } = await admin
      .from('beats')
      .update({ status: 'completed', output_path: path, duration_in_ms: durationInMs, error_message: null })
      .eq('id', beat.id)
    if (doneError) throw doneError
  } catch (error) {
    console.error(`beat ${beat.id} failed:`, error)
    await admin.from('beats')
      .update({ status: 'failed', error_message: 'Beat generation failed. Please try again.' })
      .eq('id', beat.id)
  }
  return true
}

// guest beats nobody claimed in time get deleted along with their file
async function deleteExpiredGuestBeats() {
  const { data, error } = await admin
    .from('beats').delete().is('user_id', null).lt('guest_expires_at', new Date().toISOString())
    .select('id, output_path')
  if (error) throw error
  const paths = data.map((beat) => beat.output_path).filter(Boolean)
  if (paths.length) {
    const { error: removeError } = await admin.storage.from(BEAT_BUCKET).remove(paths)
    if (removeError) throw removeError
  }
}

export async function startBeatWorker() {
  // a beat stuck on "processing" means the server stopped halfway, so do it again
  const { error } = await admin.from('beats').update({ status: 'queued' }).eq('status', 'processing')
  if (error) console.error('beat worker could not reset stuck beats:', error)

  let busy = false
  setInterval(async () => {
    if (busy) return  // still working on the last batch
    busy = true
    try {
      while (await processNextBeat()) { /* keep going until the queue is empty */ }
    } catch (error) {
      console.error('beat worker:', error)
    } finally {
      busy = false
    }
  }, POLL_MS)

  setInterval(() => {
    deleteExpiredGuestBeats().catch((error) => console.error('guest beat cleanup:', error))
  }, CLEANUP_MS)

  console.log('beat worker running (placeholder audio, generation not connected yet)')
}
