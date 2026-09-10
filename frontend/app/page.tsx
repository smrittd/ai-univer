"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api } from "@/lib/api";

export default function Home() {
  const router = useRouter();
  const [email, setEmail] = useState("demo@example.com");
  const [password, setPassword] = useState("demo-password");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function login() {
    setLoading(true); setMessage("");
    try {
      await api("/mock-data/seed", { method: "POST" });
      const token = await api<{ access_token: string }>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
      localStorage.setItem("aiu_token", token.access_token);
      router.push("/dashboard");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Unable to sign in"); }
    finally { setLoading(false); }
  }

  return <main className="grid min-h-screen place-items-center p-6"><Card className="w-full max-w-md">
    <p className="mb-2 text-sm font-semibold uppercase tracking-[.2em] text-cyan-400">AI University</p>
    <h1 className="mb-2 text-3xl font-bold">Know what to study next.</h1>
    <p className="mb-7 text-slate-400">A living, evidence-based model of your Calculus knowledge.</p>
    <div className="space-y-4">
      <label className="block text-sm">Email<input value={email} onChange={(e) => setEmail(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-3" /></label>
      <label className="block text-sm">Password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-3" /></label>
      {message && <p className="text-sm text-rose-400">{message}</p>}
      <Button className="w-full" onClick={login} disabled={loading}>{loading ? "Signing in…" : "Open my learning dashboard"}</Button>
    </div>
  </Card></main>;
}
