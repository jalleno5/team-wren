import { admin } from './supabase.js'
import { createGenerationWorker, BEAT_BUCKET } from './generation.js'
export { BEAT_BUCKET } from './generation.js'
const POLL_MS = 2000
const CLEANUP_MS = 60 * 1000
const { processNextBeat } = createGenerationWorker({ admin })

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
  // Durable leases resume in-flight jobs after a restart; never reset all jobs.

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

  console.log('beat worker running (Python music generation)')
}
