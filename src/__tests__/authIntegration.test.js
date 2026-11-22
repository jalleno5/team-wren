import { afterAll, beforeAll, describe, expect, it } from 'vitest'
import { supabase } from '../lib/supabase'


const redirectURL = `${window.location.origin}/auth/callback`

// If you want to run the user-specific tests, define both of these in the .env with REAL user credentials
const testEmail = import.meta.env.VITE_SUPABASE_TEST_EMAIL
const testPassword = import.meta.env.VITE_SUPABASE_TEST_PASSWORD


describe('Supabase Authentication Integration Tests', () => {

    beforeAll(async () => {
        await supabase.auth.signOut()
    })

    afterAll(async () => {
        await supabase.auth.signOut()
    })


    it('should initialize the Google OAuth request', async () => {
        const response = await supabase.auth.signInWithOAuth({
            provider: 'google',
            options: {
                redirectTo: redirectURL
            }
        })
        expect(response.error).toBeNull()
    })
    

    it("should use the correct OAuth redirect URL", async () => {
        const response = await supabase.auth.signInWithOAuth({
            provider: 'google',
            options: {
                redirectTo: redirectURL,
                skipBrowserRedirect: true,
            },
        })
        expect(response.error).toBeNull()

        const oauthURL = new URL(response.data.url)
        expect(oauthURL.searchParams.get("redirect_to")).toBe(redirectURL)
    })


    it("should be Google as the provider", async () => {
        const response = await supabase.auth.signInWithOAuth({
            provider: 'google',
            options: {
                redirectTo: redirectURL,
                skipBrowserRedirect: true,
            },
        })
        expect(response.error).toBeNull()
        expect(response.data.provider).toBe("google")

        const oauthURL = new URL(response.data.url)
        expect(oauthURL.searchParams.get("provider")).toBe("google")
    })


    it.runIf(testEmail && testPassword)("should authenticate a user with email and password after signing in", async () => {
        const response = await supabase.auth.signInWithPassword({
            email: testEmail,
            password: testPassword,
        })

        expect(response.error).toBeNull()
        expect(response.data.session).toBeDefined()
        expect(response.data.session?.access_token).toBeTruthy()
        expect(response.data.user).toBeDefined()
        expect(response.data.user?.email).toBe(testEmail)
    })


    it.runIf(testEmail && testPassword)("should end the session after signing out", async () => {
        const signInResponse = await supabase.auth.signInWithPassword({
            email: testEmail,
            password: testPassword,
        })
        expect(signInResponse.error).toBeNull()
        expect(signInResponse.data.session).toBeDefined()
        
        const signOutResponse = await supabase.auth.signOut()
        expect(signOutResponse.error).toBeNull()

        const sessionResponse = await supabase.auth.getSession()
        expect(sessionResponse.error).toBeNull()
        expect(sessionResponse.data.session).toBeNull()
    })

})