import { describe, expect, it } from 'vitest'
import { supabase } from '../lib/supabase'


describe('Supabase Authentication Integration', () => {

    it('should initialize the Google OAuth request', async () => {

        const response = await supabase.auth.signInWithOAuth({
            provider: 'google',
            options: {
                redirectTo: `${window.location.origin}/auth/callback`,
            }
        })

        expect(response.error).toBeNull()
        expect(response.data.provider).toBe('google')
        expect(response.data.url).toContain('provider=google')

    })

})