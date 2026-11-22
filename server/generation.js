import { workerRequest } from '../Pattern_Testing/integration/worker-client.js'
import { generationPrompt, wavDurationMs } from './generation-utils.js'

export const BEAT_BUCKET = 'beats'
export function createGenerationWorker({ admin, request = workerRequest }) {
  async function save(job, changes) {
    const result = await admin.from('beat_worker_jobs').update(changes)
      .eq('beat_id', job.beat_id).eq('lease_token', job.lease_token)
    if (result.error) throw result.error
  }
  return {
    async processNextBeat() {
      const claimed = await admin.rpc('claim_beat_generation')
      if (claimed.error) throw claimed.error
      const job = claimed.data
      if (!job) return false
      try {
        const found = await admin.from('beats').select('id,user_id,speed,genre,sounds_beats(sound_id,category)')
          .eq('id', job.beat_id).maybeSingle()
        if (found.error) throw found.error
        if (!found.data) return false
        const beat = found.data
        if (!job.worker_job_id) {
          const sources = []
          for (const link of beat.sounds_beats) {
            const result = await admin.from('sounds').select('id,user_id,visibility,storage_path,classification')
              .eq('id', link.sound_id).maybeSingle()
            if (result.error) throw result.error
            const sound = result.data
            // Recheck access after queuing. Guests and claimed guest jobs may
            // use public sounds; members may additionally use their own sounds.
            if (!sound || (sound.visibility !== 'public' && sound.user_id !== beat.user_id)) {
              throw Object.assign(new Error('A selected sound is no longer accessible'), { terminal: true })
            }
            const bucket = sound.visibility === 'public' ? 'sounds-public' : 'sounds-private'
            const signed = await admin.storage.from(bucket).createSignedUrl(sound.storage_path, 600)
            if (signed.error) throw signed.error
            sources.push({ file: sound.id, audio_url: signed.data.signedUrl,
              classification: link.category || sound.classification })
          }
          if (!sources.length) throw Object.assign(new Error('No sounds selected'), { terminal: true })
          const submitted = await request('/music/jobs', { method: 'POST', body: {
            job_id: beat.id, prompt: generationPrompt({ ...beat, prompt: job.prompt }), duration: job.duration,
            sounds: sources.map(({ file }) => ({ file })), sample_sources: sources,
          } })
          const result = await submitted.json()
          if (result.id !== beat.id) throw new Error('Unexpected worker job ID')
          job.worker_job_id = result.id
          await save(job, { worker_job_id: result.id })
        }
        const state = await (await request(`/music/jobs/${job.worker_job_id}`)).json()
        if (state.status === 'failed') throw Object.assign(new Error('Music processing failed'), { terminal: true })
        if (state.status !== 'completed') return false
        if (state.result?.render_error || !state.result?.artifacts?.rendered) {
          throw Object.assign(new Error('No compatible rendered beat was produced'), { terminal: true })
        }
        const audio = new Uint8Array(await (await request(`/music/jobs/${job.worker_job_id}/artifacts/rendered`)).arrayBuffer())
        const duration = wavDurationMs(audio)
        const path = `${beat.id}.wav`
        const upload = await admin.storage.from(BEAT_BUCKET).upload(path, audio, { contentType: 'audio/wav', upsert: true })
        if (upload.error) throw upload.error
        // Completion checks the lease and guest expiry atomically. If cleanup
        // deleted the beat while uploading, remove the otherwise orphaned file.
        const done = await admin.rpc('finish_beat_generation', {
          p_beat_id: beat.id, p_lease_token: job.lease_token,
          p_status: 'completed', p_output_path: path, p_duration: duration, p_error: null,
        })
        if (done.error) throw done.error
        if (!done.data) {
          const current = await admin.from('beats').select('id,user_id,guest_expires_at').eq('id', beat.id).maybeSingle()
          if (!current.error && (!current.data || (!current.data.user_id && Date.parse(current.data.guest_expires_at) <= Date.now()))) {
            await admin.storage.from(BEAT_BUCKET).remove([path])
          }
        }
      } catch (error) {
        const terminal = error.terminal || [400, 401, 403, 404, 422].includes(error.status)
        if (terminal) {
          const failed = await admin.rpc('finish_beat_generation', {
            p_beat_id: job.beat_id, p_lease_token: job.lease_token, p_status: 'failed',
            p_output_path: null, p_duration: null,
            p_error: 'Beat generation failed. Check the selected sounds and musical roles, then try again.',
          })
          if (failed.error) throw failed.error
        } else {
          // Network, queue-capacity and storage errors retain the same job ID.
          console.error(`Beat ${job.beat_id} will be retried:`, error.message)
        }
      } finally {
        await save(job, { lease_until: new Date(Date.now() + 2000).toISOString() })
      }
      return true
    },
  }
}
