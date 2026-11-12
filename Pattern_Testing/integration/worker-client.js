// Server-side only: use from Vercel handlers AFTER checking the user's Supabase session.
// Keep the association {user_id, worker_job_id} in your DB and check ownership on
// every status/download request. A worker ID alone is not user authorization.
export async function workerRequest(path, { method = 'GET', body } = {}) {
  const response = await fetch(`${process.env.MUSIC_WORKER_URL}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${process.env.MUSIC_API_KEY}`,
      ...(body ? { 'Content-Type': 'application/json' } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  if (!response.ok) throw new Error(`Music worker returned ${response.status}`);
  return response;
}

export async function createMusicJob(prompt, duration = 10, mapping) {
  return (await workerRequest('/music/jobs', {
    method: 'POST', body: { prompt, duration, mapping },
  })).json();
}

export async function getMusicJob(id) {
  return (await workerRequest(`/music/jobs/${encodeURIComponent(id)}`)).json();
}

// Optional drum replacement + preserved accompaniment. Check source job ownership.
// Provide either {prompt, duration} or {source_job_id}, plus {mapping} or {sounds}.
export async function createPercussionJob(options) {
  return (await workerRequest('/music/percussion-jobs', {
    method: 'POST', body: options,
  })).json();
}

// Check ownership of sourceJobId in your authenticated route before calling.
export async function createSoundMapping(sounds, sourceJobId, fallback = 'nearest') {
  return (await workerRequest('/music/mappings', {
    method: 'POST', body: { sounds, source_job_id: sourceJobId, fallback },
  })).json();
}

// Pass a server-side Supabase client. Bucket must be private; objectPath should
// be derived on the server as `${user.id}/${jobId}/transcribed.mid`.
export async function saveMidiToSupabase(supabase, id, objectPath) {
  const response = await workerRequest(`/music/jobs/${encodeURIComponent(id)}/artifacts/midi`);
  const midi = new Uint8Array(await response.arrayBuffer());
  const { error } = await supabase.storage.from('music-artifacts').upload(objectPath, midi, {
    contentType: 'audio/midi', upsert: true,
  });
  if (error) throw error;
  const result = await supabase.storage.from('music-artifacts').createSignedUrl(objectPath, 3600);
  if (result.error) throw result.error;
  return result.data.signedUrl;
}
