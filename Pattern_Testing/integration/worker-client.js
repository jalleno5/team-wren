// Server-side only: use from Vercel handlers AFTER checking the user's Supabase session.
// Keep the association {user_id, worker_job_id} in your DB and check ownership on
// every status/download request. A worker ID alone is not user authorization.
export async function workerRequest(path, { method = 'GET', body, supabaseAccessToken } = {}) {
  const response = await fetch(`${process.env.MUSIC_WORKER_URL.replace(/\/$/, '')}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${process.env.MUSIC_API_KEY}`,
      ...(supabaseAccessToken ? { 'X-Supabase-Authorization': `Bearer ${supabaseAccessToken}` } : {}),
      ...(body ? { 'Content-Type': 'application/json' } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
    signal: AbortSignal.timeout(method === 'POST' ? 120_000 : 60_000),
  });
  if (!response.ok) {
    const error = new Error(`Music worker returned ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return response;
}

// For automatic assignment, pass sounds=[{file: soundId}] and omit mapping.
export async function createMusicJob(prompt, duration = 10, mapping, supabaseAccessToken, sounds) {
  return (await workerRequest('/music/jobs', {
    method: 'POST', body: { prompt, duration, mapping, sounds }, supabaseAccessToken,
  })).json();
}

export async function getMusicJob(id) {
  return (await workerRequest(`/music/jobs/${encodeURIComponent(id)}`)).json();
}

// Optional drum replacement + preserved accompaniment. Check source job ownership.
// Provide either {prompt, duration} or {source_job_id}, plus {mapping} or {sounds}.
export async function createPercussionJob(options, supabaseAccessToken) {
  return (await workerRequest('/music/percussion-jobs', {
    method: 'POST', body: options, supabaseAccessToken,
  })).json();
}

// Check ownership of sourceJobId in your authenticated route before calling.
export async function createSoundMapping(sounds, sourceJobId, fallback = 'nearest', supabaseAccessToken) {
  return (await workerRequest('/music/mappings', {
    method: 'POST', body: { sounds, source_job_id: sourceJobId, fallback }, supabaseAccessToken,
  })).json();
}

export async function createMusicRender(sourceJobId, mapping, supabaseAccessToken, sounds) {
  return (await workerRequest('/music/renders', {
    method: 'POST', body: { source_job_id: sourceJobId, mapping, sounds }, supabaseAccessToken,
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
