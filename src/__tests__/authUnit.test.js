import { beforeEach, describe, expect, it, vi } from 'vitest'
import { supabase } from '../lib/supabase'


const redirectURL = `${window.location.origin}/auth/callback`


const { signInWithOAuth, signOut } = vi.hoisted(() => ({
    signInWithOAuth: vi.fn(),
    signOut: vi.fn()
}))


vi.mock("@supabase/supabase-js", () => ({
    createClient: vi.fn(() => ({
        auth: {
            signInWithOAuth,
            signOut,
        }
    })),
}))


describe("Supabase Authentication Unit Tests", () => {

    beforeEach(() => {
        vi.clearAllMocks()
    })


    it("should authenticate using Google", async () => {
        signInWithOAuth.mockResolvedValue({
            data: {
                provider: "google",
                url: "https://accounts.google.com"
            },
            error: null
        })

        await supabase.auth.signInWithOAuth({
            provider: "google",
            options: {
                redirectTo: redirectURL
            }
        })

        expect(signInWithOAuth).toHaveBeenCalledWith({
            provider: "google",
            options: {
                redirectTo: redirectURL
            }
        })
    })


    it("should handle Google OAuth errors", async () => {
        const error = new Error("Google authentication failed")

        signInWithOAuth.mockResolvedValue({
            data: {
                provider: null,
                url: null,
            },
            error,
        })

        const response = await supabase.auth.signInWithOAuth({
            provider: 'google',
            options: {
                redirectTo: redirectURL,
            },
        })
        expect(response.error).toBe(error)
    })


    it("should sign out successfully", async () => {
        signOut.mockResolvedValue({
            error: null
        })
        const response = await supabase.auth.signOut()
        expect(response.error).toBeNull()
        expect(signOut).toHaveBeenCalled()
    })


    it("should handle sign out errors", async () => {
        const error = new Error("Sign out failed")
        signOut.mockResolvedValue({
            error
        })
        const response = await supabase.auth.signOut()
        expect(response.error).toBe(error)
        expect(signOut).toHaveBeenCalled()
    })
        
})