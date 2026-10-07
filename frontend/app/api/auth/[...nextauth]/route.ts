import NextAuth from "next-auth"
import GithubProvider from "next-auth/providers/github"
import type { Profile } from "next-auth"

interface GithubProfile extends Profile {
  id: number
  login: string
  avatar_url: string
}

const handler = NextAuth({
  providers: [
    GithubProvider({
      clientId: process.env.GITHUB_CLIENT_ID as string,
      clientSecret: process.env.GITHUB_CLIENT_SECRET as string,
      authorization: {
        params: {
          scope: "read:user user:email repo admin:repo_hook",
        },
      },
    }),
  ],
  callbacks: {
    async jwt({ token, account, profile }) {
      if (account) {
        token.accessToken = account.access_token ?? ""
        const githubProfile = profile as GithubProfile
        token.githubId = githubProfile?.id?.toString() ?? ""
      }
      return token
    },
    async session({ session, token }) {
      session.accessToken = (token.accessToken ?? "") as string
      session.githubId = (token.githubId ?? "") as string
      return session
    },
        async signIn({ account, profile }) {
          const githubProfile = profile as GithubProfile
      if (account?.access_token && githubProfile?.id) {
        try {
          const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
          await fetch(`${apiUrl}/auth/sync-token`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              github_id: githubProfile.id.toString(),
              github_token: account.access_token
            })
          })
        } catch (err) {
          console.error("Token sync failed:", err)
        }
      }
      return true
    }
    
  },
    
  
  pages: {
    signIn: "/login",
  },
})

export { handler as GET, handler as POST }