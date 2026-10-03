"use client"

import { signIn } from "next-auth/react"
import { Button } from "@/components/ui/button"
import { GitBranch } from "lucide-react"


export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950">
      <div className="bg-slate-900 p-8 rounded-xl border border-slate-800 w-full max-w-md">
        
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">
            FirstSenior
          </h1>
          <p className="text-slate-400">
            The AI senior engineer you never had
          </p>
        </div>

        <div className="space-y-4 mb-8">
          <div className="flex items-center gap-3 text-slate-300">
            <span className="text-green-400">✓</span>
            <span>AI reviews your code on every push</span>
          </div>
          <div className="flex items-center gap-3 text-slate-300">
            <span className="text-green-400">✓</span>
            <span>Remembers your personal mistake patterns</span>
          </div>
          <div className="flex items-center gap-3 text-slate-300">
            <span className="text-green-400">✓</span>
            <span>Auto-writes your project diary</span>
          </div>
          <div className="flex items-center gap-3 text-slate-300">
            <span className="text-green-400">✓</span>
            <span>Weekly mentor report every Monday</span>
          </div>
        </div>

        <Button
          onClick={() => signIn("github", { callbackUrl: "/dashboard" })}
          className="w-full bg-white text-black hover:bg-slate-200 font-semibold py-6"
        >
          <GitBranch className="mr-2 h-5 w-5" />
          Continue with GitHub
        </Button>

        <p className="text-center text-slate-500 text-sm mt-4">
          We only access your repositories to review code.
          We never modify your code.
        </p>
      </div>
    </div>
  )
}