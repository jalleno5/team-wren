import { HttpError } from './http.js'


export function generationPrompt({ prompt, genre, speed }) {
  const description = prompt?.trim() || 'Create a coherent instrumental beat.'
  return `${description}\nStyle: ${genre?.trim() || 'a balanced groove'}. Tempo: approximately ${speed} BPM. Use a clear rhythm and complementary instrumental parts.`
}

// Read the actual PCM WAV duration, including sample tails, rather than assuming
// that MusicGen and the renderer produce exactly the requested number of seconds.
export function wavDurationMs(bytes) {
  const buffer = Buffer.from(bytes)
  if (buffer.length < 12 || buffer.toString('ascii', 0, 4) !== 'RIFF' || buffer.toString('ascii', 8, 12) !== 'WAVE') {
    throw new HttpError(502, 'The music worker returned an invalid WAV file')
  }
  let rate, size
  for (let offset = 12; offset + 8 <= buffer.length;) {
    const kind = buffer.toString('ascii', offset, offset + 4)
    const length = buffer.readUInt32LE(offset + 4)
    const end = offset + 8 + length
    if (end > buffer.length) throw new HttpError(502, 'The music worker returned an incomplete WAV file')
    if (kind === 'fmt ' && length >= 16) rate = buffer.readUInt32LE(offset + 16)
    if (kind === 'data') size = length
    offset = end + (length % 2)
  }
  if (!rate || !size) throw new HttpError(502, 'The music worker returned an empty WAV file')
  return Math.max(1, Math.round(size / rate * 1000))
}
