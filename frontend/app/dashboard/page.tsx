"use client"

import { useSession, signOut } from "next-auth/react"
import { useRouter } from "next/navigation"
import { useEffect, useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import ReactMarkdown from "react-markdown"
import axios from "axios"

const API_URL = process.env.NEXT_PUBLIC_API_URL

interface GithubRepo {
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

interface Review {
  id: number
  repo_name?: string
  commit_sha: string
  files_changed: string
  ai_review: string
  health_score: number
  created_at: string
}

interface DiaryEntry {
  id: number
  commit_sha: string
  summary: string
  changes_made: string
  senior_feedback: string
  created_at: string
}

export default function DashboardPage() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const queryClient = useQueryClient()

  const [selectedRepo, setSelectedRepo] = useState<ConnectedRepo | null>(null)
  const [showRepoList, setShowRepoList] = useState(false)
  const [selectedReview, setSelectedReview] = useState<Review | null>(null)

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login")
    }
  }, [status, router])

  // Fetch connected repos
  const { data: connectedRepos = [], isLoading: reposLoading, error: reposError } = useQuery({
    queryKey: ["connectedRepos", session?.githubId],
    queryFn: async () => {
      const res = await axios.get(`${API_URL}/repos/connected`, {
        params: { github_id: session?.githubId }
      })
      return res.data as ConnectedRepo[]
    },
    enabled: !!session?.githubId,
    refetchInterval: 30000
  })

  // Set first repo as selected when repos load
  useEffect(() => {
    if (connectedRepos.length > 0 && !selectedRepo) {
      setSelectedRepo(connectedRepos[0])
    }
  }, [connectedRepos, selectedRepo])

  // Fetch GitHub repos for picker
  const { data: githubRepos = [], isLoading: githubLoading, refetch: fetchGithubRepos } = useQuery({
    queryKey: ["githubRepos", session?.accessToken],
    queryFn: async () => {
      const res = await axios.get(`${API_URL}/repos/list`, {
        params: { github_token: session?.accessToken }
      })
      return res.data as GithubRepo[]
    },
    enabled: false
  })

  // Fetch reviews for selected repo
  const { data: reviews = [], isLoading: reviewsLoading } = useQuery({
    queryKey: ["reviews", selectedRepo?.id],
    queryFn: async () => {
      const res = await axios.get(`${API_URL}/reviews/${selectedRepo?.id}`)
      return res.data as Review[]
    },
    enabled: !!selectedRepo?.id
  })

  // Fetch diary for selected repo
  const { data: diary = [], isLoading: diaryLoading } = useQuery({
    queryKey: ["diary", selectedRepo?.id],
    queryFn: async () => {
      const res = await axios.get(`${API_URL}/diary/${selectedRepo?.id}`)
      return res.data as DiaryEntry[]
    },
    enabled: !!selectedRepo?.id
  })

  // Connect repo mutation
  const connectMutation = useMutation({
    mutationFn: async (repo: GithubRepo) => {
      await axios.post(`${API_URL}/repos/connect`, null, {
        params: {
          github_token: session?.accessToken,
          github_id: session?.githubId,
          repo_full_name: repo.full_name,
          repo_name: repo.name,
          github_repo_id: String(repo.id)
        }
      })
    },
    onSuccess: () => {
      setShowRepoList(false)
      queryClient.invalidateQueries({ queryKey: ["connectedRepos"] })
    },
    onError: (err: any) => {
      if (err.response?.data?.detail === "Repository already connected") {
        alert("Already connected")
      }
    }
  })

  const getHealthColor = (score: number) => {
    if (score >= 80) return "text-green-400"
    if (score >= 60) return "text-yellow-400"
    return "text-red-400"
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    })
  }

  const currentRepo = connectedRepos.find(r => r.id === selectedRepo?.id) || selectedRepo

  if (status === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950">
        <p className="text-white">Loading...</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950">

      {/* Header */}
      <div className="border-b border-slate-800 px-8 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <h1 className="text-xl font-bold text-white">FirstSenior 🚀</h1>
          <div className="flex items-center gap-4">
            <img
              src={session?.user?.image || ""}
              alt="avatar"
              className="w-8 h-8 rounded-full"
            />
            <span className="text-slate-300 text-sm">{session?.user?.name}</span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => signOut({ callbackUrl: "/login" })}
              className="border-slate-700 text-slate-300"
            >
              Sign out
            </Button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-8">
        <div className="grid grid-cols-12 gap-6">

          {/* Left Sidebar */}
          <div className="col-span-3">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-white font-semibold">Repositories</h2>
              <Button
                size="sm"
                onClick={() => {
                  fetchGithubRepos()
                  setShowRepoList(true)
                }}
                disabled={githubLoading}
                className="bg-green-600 hover:bg-green-700 text-white text-xs"
              >
                {githubLoading ? "Loading..." : "+ Add"}
              </Button>
            </div>

            {reposError && (
              <p className="text-red-400 text-sm mb-4">
                Failed to load repositories
              </p>
            )}

            {reposLoading ? (
              <div className="space-y-2">
                {[1, 2].map(i => (
                  <div key={i} className="h-20 bg-slate-800 rounded-lg animate-pulse" />
                ))}
              </div>
            ) : (
              <div className="space-y-2">
                {connectedRepos.map((repo) => (
                  <div
                    key={repo.id}
                    onClick={() => setSelectedRepo(repo)}
                    className={`p-4 rounded-lg border cursor-pointer transition-colors ${
                      selectedRepo?.id === repo.id
                        ? "border-green-600 bg-slate-800"
                        : "border-slate-800 bg-slate-900 hover:border-slate-600"
                    }`}
                  >
                    <p className="text-white font-medium text-sm">{repo.name}</p>
                    <p className={`text-lg font-bold mt-1 ${getHealthColor(repo.health_score)}`}>
                      {repo.health_score}/100
                    </p>
                    <p className="text-slate-500 text-xs">Health Score</p>
                  </div>
                ))}

                {connectedRepos.length === 0 && (
                  <Card className="bg-slate-900 border-slate-800 p-4 text-center">
                    <p className="text-slate-400 text-sm">No repos connected</p>
                  </Card>
                )}
              </div>
            )}
          </div>

          {/* Main Content */}
          <div className="col-span-9">
            {currentRepo ? (
              <>
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h2 className="text-2xl font-bold text-white">
                      {currentRepo.name}
                    </h2>
                    <p className="text-slate-400 text-sm">{currentRepo.full_name}</p>
                  </div>
                  <div className="text-right">
                    <p className={`text-4xl font-bold ${getHealthColor(currentRepo.health_score)}`}>
                      {currentRepo.health_score}/100
                    </p>
                    <p className="text-slate-500 text-sm">Current Health Score</p>
                  </div>
                </div>

                <Tabs defaultValue="reviews">
                  <TabsList className="bg-slate-900 border border-slate-800 mb-6">
                    <TabsTrigger value="reviews" className="text-slate-300">
                      Reviews ({reviews.length})
                    </TabsTrigger>
                    <TabsTrigger value="diary" className="text-slate-300">
                      Project Diary ({diary.length})
                    </TabsTrigger>
                  </TabsList>

                  {/* Reviews Tab */}
                  <TabsContent value="reviews">
                    {reviewsLoading ? (
                      <div className="space-y-4">
                        {[1, 2].map(i => (
                          <div key={i} className="h-24 bg-slate-800 rounded-lg animate-pulse" />
                        ))}
                      </div>
                    ) : reviews.length === 0 ? (
                      <Card className="bg-slate-900 border-slate-800 p-8 text-center">
                        <p className="text-slate-400">No reviews yet</p>
                        <p className="text-slate-500 text-sm mt-2">
                          Push code to get your first AI review
                        </p>
                      </Card>
                    ) : (
                      <div className="space-y-4">
                        {reviews.map((review) => (
                          <Card
                            key={review.id}
                            className="bg-slate-900 border-slate-800 p-6 cursor-pointer hover:border-slate-600 transition-colors"
                            onClick={() => setSelectedReview(
                              selectedReview?.id === review.id ? null : review
                            )}
                          >
                            <div className="flex items-center justify-between mb-3">
                              <div className="flex items-center gap-3">
                                <Badge
                                  variant="outline"
                                  className="text-slate-400 border-slate-700 font-mono"
                                >
                                  {review.commit_sha}
                                </Badge>
                                <span className="text-slate-400 text-sm">
                                  {formatDate(review.created_at)}
                                </span>
                              </div>
                              <span className={`font-bold ${getHealthColor(review.health_score)}`}>
                                {review.health_score}/100
                              </span>
                            </div>
                            <p className="text-slate-400 text-sm mb-3">
                              Files: {review.files_changed}
                            </p>
                            {selectedReview?.id === review.id && (
                              <div className="mt-4 pt-4 border-t border-slate-800 text-sm text-slate-300 leading-7 [&>h2]:text-white [&>h2]:text-lg [&>h2]:font-bold [&>h2]:mt-4 [&>h3]:text-green-400 [&>h3]:font-semibold [&>h3]:mt-3 [&>ul]:ml-4 [&>ul]:list-disc [&>p]:my-2 [&>pre]:bg-slate-800 [&>pre]:p-3 [&>pre]:rounded [&>pre]:overflow-x-auto [&>code]:text-green-300 [&>strong]:text-yellow-400">
                                <ReactMarkdown>{review.ai_review}</ReactMarkdown>
                              </div>
                            )}
                          </Card>
                        ))}
                      </div>
                    )}
                  </TabsContent>

                  {/* Diary Tab */}
                  <TabsContent value="diary">
                    {diaryLoading ? (
                      <div className="space-y-4">
                        {[1, 2].map(i => (
                          <div key={i} className="h-24 bg-slate-800 rounded-lg animate-pulse" />
                        ))}
                      </div>
                    ) : diary.length === 0 ? (
                      <Card className="bg-slate-900 border-slate-800 p-8 text-center">
                        <p className="text-slate-400">No diary entries yet</p>
                        <p className="text-slate-500 text-sm mt-2">
                          Push code to start your project diary
                        </p>
                      </Card>
                    ) : (
                      <div className="relative">
                        <div className="absolute left-4 top-0 bottom-0 w-px bg-slate-800" />
                        <div className="space-y-6">
                          {diary.map((entry) => (
                            <div key={entry.id} className="relative pl-10">
                              <div className="absolute left-3 top-2 w-3 h-3 rounded-full bg-green-600 border-2 border-slate-950" />
                              <Card className="bg-slate-900 border-slate-800 p-5">
                                <div className="flex items-center gap-3 mb-3">
                                  <Badge
                                    variant="outline"
                                    className="text-slate-400 border-slate-700 font-mono text-xs"
                                  >
                                    {entry.commit_sha}
                                  </Badge>
                                  <span className="text-slate-500 text-xs">
                                    {formatDate(entry.created_at)}
                                  </span>
                                </div>
                                <p className="text-white font-medium mb-2">
                                  {entry.summary}
                                </p>
                                <p className="text-slate-400 text-sm mb-3">
                                  Changed: {entry.changes_made}
                                </p>
                                <div className="bg-slate-800 rounded-lg p-3">
                                  <p className="text-slate-300 text-sm">
                                    {entry.senior_feedback}
                                  </p>
                                </div>
                              </Card>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </TabsContent>
                </Tabs>
              </>
            ) : (
              <Card className="bg-slate-900 border-slate-800 p-8 text-center">
                <p className="text-slate-400">Select a repository to view reviews</p>
              </Card>
            )}
          </div>
        </div>
      </div>

      {/* Repo Picker Modal */}
      {showRepoList && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <Card className="bg-slate-900 border-slate-800 w-full max-w-2xl max-h-[80vh] overflow-hidden">
            <div className="p-6 border-b border-slate-800 flex items-center justify-between">
              <h3 className="text-white font-semibold">Select a Repository</h3>
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
                        <Badge variant="outline" className="text-slate-400 border-slate-700 text-xs">
                          {repo.language}
                        </Badge>
                      )}
                      {repo.private && (
                        <Badge variant="outline" className="text-slate-400 border-slate-700 text-xs">
                          Private
                        </Badge>
                      )}
                    </div>
                    {repo.description && (
                      <p className="text-slate-500 text-xs mt-1">{repo.description}</p>
                    )}
                  </div>
                  <Button
                    onClick={() => connectMutation.mutate(repo)}
                    disabled={connectMutation.isPending}
                    className="bg-green-600 hover:bg-green-700 text-white ml-4"
                  >
                    
                    {connectMutation.isPending ? "Connecting..." : "Connect"}
                  </Button>
                </div>
              ))}
            </div>
          </Card>

        </div>
      )}
    </div>
  )
}