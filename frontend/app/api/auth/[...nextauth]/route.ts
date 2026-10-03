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
  },
  pages: {
    signIn: "/login",
  },
})

export { handler as GET, handler as POST }