import { readFileSync } from 'node:fs'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// Replace the real Supabase library with a fake, so these tests never
// connect to the real database and don't need real keys
vi.mock('@supabase/supabase-js', () => ({
  createClient: vi.fn(() => ({ from: vi.fn() })),
}))

// supabase.js creates the client the moment it's imported, so the env
// variables have to be set first. This loads a fresh copy of the file
// (and the fake library) after they're set.
async function loadSupabase() {
  vi.resetModules()
  const { createClient } = await import('@supabase/supabase-js')
  const { supabase } = await import('../lib/supabase.js')
  return { createClient, supabase }
}

describe("Supabase client", () => {
  beforeEach(() => {
    vi.stubEnv('VITE_SUPABASE_URL', 'https://test-project.supabase.co')
    vi.stubEnv('VITE_SUPABASE_ANON_KEY', 'test-anon-key')
  })

  afterEach(() => {
    vi.unstubAllEnvs()
    vi.clearAllMocks()
  })

  it("is created with the URL and key from the env variables", async () => {
    const { createClient } = await loadSupabase()

    expect(createClient).toHaveBeenCalledTimes(1)
    expect(createClient).toHaveBeenCalledWith('https://test-project.supabase.co', 'test-anon-key')
  })

  it("exports the client that createClient made", async () => {
    const { createClient, supabase } = await loadSupabase()

    expect(supabase).toBe(createClient.mock.results[0].value)
  })
})

describe(".env.example", () => {
  it("lists every env variable the Supabase client needs", () => {
    const example = readFileSync('.env.example', 'utf8')

    expect(example).toMatch(/^VITE_SUPABASE_URL=/m)
    expect(example).toMatch(/^VITE_SUPABASE_ANON_KEY=/m)
  })
})
