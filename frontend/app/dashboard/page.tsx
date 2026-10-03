"use client"

import { useSession, signOut } from "next-auth/react"
import { useRouter } from "next/navigation"
import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import axios from "axios"

interface GitHubRepo {
  id: number
  name: string
  full_name: string
  private: boolean
  description: string
  language: string
}

interface ConnectedRepo {
  id: number
  name: string
  full_name: string
  health_score: number
  created_at: string
}

export default function DashboardPage() {
  const { data: session, status } = useSession()
  const router = useRouter()

  const [githubRepos, setGithubRepos] = useState<GitHubRepo[]>([])
  const [connectedRepos, setConnectedRepos] = useState<ConnectedRepo[]>([])
  const [showRepoList, setShowRepoList] = useState(false)
  const [loading, setLoading] = useState(false)
  const [connecting, setConnecting] = useState<number | null>(null)

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/login")
    }
  }, [status, router])

  useEffect(() => {
    if (session?.accessToken && session?.githubId) {
      fetchConnectedRepos()
    }
  }, [session])

  const fetchConnectedRepos = async () => {
    try {
      const res = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/repos/connected`,
        { params: { github_id: session?.githubId } }
      )
      setConnectedRepos(res.data)
    } catch (err) {
      console.error("Failed to fetch connected repos", err)
    }
  }

  const fetchGithubRepos = async () => {
    setLoading(true)
    try {
      const res = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/repos/list`,
        { params: { github_token: session?.accessToken } }
      )
      setGithubRepos(res.data)
      setShowRepoList(true)
    } catch (err) {
      console.error("Failed to fetch repos", err)
    } finally {
      setLoading(false)
    }
  }

  const connectRepo = async (repo: GitHubRepo) => {
    setConnecting(repo.id)
    try {
      await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/repos/connect`,
        null,
        {
          params: {
            github_token: session?.accessToken,
            github_id: session?.githubId,
            repo_full_name: repo.full_name,
            repo_name: repo.name,
            github_repo_id: String(repo.id)
          }
        }
      )
      setShowRepoList(false)
      fetchConnectedRepos()
    } catch (err: any) {
      if (err.response?.data?.detail === "Repository already connected") {
        alert("This repository is already connected")
      }
    } finally {
      setConnecting(null)
    }
  }

  const getHealthColor = (score: number) => {
    if (score >= 80) return "text-green-400"
    if (score >= 60) return "text-yellow-400"
    return "text-red-400"
  }

  if (status === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950">
        <p className="text-white">Loading...</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950 p-8">
      <div className="max-w-6xl mx-auto">

        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-2xl font-bold text-white">FirstSenior</h1>
          <div className="flex items-center gap-4">
            <img
              src={session?.user?.image || ""}
              alt="avatar"
              className="w-8 h-8 rounded-full"
            />
            <span className="text-slate-300">{session?.user?.name}</span>
            <Button
              variant="outline"
              onClick={() => signOut({ callbackUrl: "/login" })}
              className="border-slate-700 text-slate-300"
            >
              Sign out
            </Button>
          </div>
        </div>

        {/* Connected Repos */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-white">
              Connected Repositories
            </h2>
            <Button
              onClick={fetchGithubRepos}
              disabled={loading}
              className="bg-green-600 hover:bg-green-700 text-white"
            >
              {loading ? "Loading..." : "+ Connect Repository"}
            </Button>
          </div>

          {connectedRepos.length === 0 && !showRepoList && (
            <Card className="bg-slate-900 border-slate-800 p-8 text-center">
              <p className="text-slate-400 mb-2">No repositories connected yet</p>
              <p className="text-slate-500 text-sm">
                Connect a GitHub repository to start getting AI mentor reviews
              </p>
            </Card>
          )}

          {connectedRepos.length > 0 && (
            <div className="grid gap-4">
              {connectedRepos.map((repo) => (
                <Card
                  key={repo.id}
                  className="bg-slate-900 border-slate-800 p-6"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-white font-semibold text-lg">
                        {repo.name}
                      </h3>
                      <p className="text-slate-400 text-sm">{repo.full_name}</p>
                    </div>
                    <div className="text-right">
                      <p className={`text-2xl font-bold ${getHealthColor(repo.health_score)}`}>
                        {repo.health_score}/100
                      </p>
                      <p className="text-slate-500 text-xs">Health Score</p>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>

        {/* GitHub Repo Picker */}
        {showRepoList && (
          <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
            <Card className="bg-slate-900 border-slate-800 w-full max-w-2xl max-h-[80vh] overflow-hidden">
              <div className="p-6 border-b border-slate-800 flex items-center justify-between">
                <h3 className="text-white font-semibold text-lg">
                  Select a Repository
                </h3>
                <Button
                  variant="ghost"
                  onClick={() => setShowRepoList(false)}
                  className="text-slate-400"
                >
                  ✕
                </Button>
              </div>
              <div className="overflow-y-auto max-h-[60vh] p-4 space-y-2">
                {githubRepos.map((repo) => (
                  <div
                    key={repo.id}
                    className="flex items-center justify-between p-4 rounded-lg border border-slate-800 hover:border-slate-600 transition-colors"
                  >
                    <div>
                      <p className="text-white font-medium">{repo.name}</p>
                      <div className="flex items-center gap-2 mt-1">
                        {repo.language && (
                          <Badge
                            variant="outline"
                            className="text-slate-400 border-slate-700 text-xs"
                          >
                            {repo.language}
                          </Badge>
                        )}
                        {repo.private && (
                          <Badge
                            variant="outline"
                            className="text-slate-400 border-slate-700 text-xs"
                          >
                            Private
                          </Badge>
                        )}
                      </div>
                      {repo.description && (
                        <p className="text-slate-500 text-xs mt-1">
                          {repo.description}
                        </p>
                      )}
                    </div>
                    <Button
                      onClick={() => connectRepo(repo)}
                      disabled={connecting === repo.id}
                      className="bg-green-600 hover:bg-green-700 text-white ml-4"
                    >
                      {connecting === repo.id ? "Connecting..." : "Connect"}
                    </Button>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        )}

      </div>
    </div>
  )
}