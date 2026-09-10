"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Activity, AlertTriangle, ArrowRight, BrainCircuit, Network } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { Analysis, TopicResult } from "@/types/analysis";

type Course = { id: string; title: string; code: string; description: string };

const tone: Record<string, string> = {
  MASTERED: "bg-emerald-400", PARTIALLY_UNDERSTOOD: "bg-amber-300", APPLICATION_PROBLEM: "bg-orange-400",
  WEAK: "bg-orange-500", CRITICAL: "bg-rose-500", FORGOTTEN: "bg-violet-400", NEVER_LEARNED: "bg-slate-500",
};

function TopicRow({ topic }: { topic: TopicResult }) {
  return <div className="grid grid-cols-[1fr_auto] gap-3 border-t border-slate-800 py-3 first:border-0">
    <div><div className="font-medium">{topic.topic_title}</div><div className="text-xs text-slate-400">{topic.state.replaceAll("_", " ")} · {topic.confidence}% confidence</div></div>
    <div className="flex items-center gap-2"><div className="h-2 w-20 overflow-hidden rounded-full bg-slate-800"><div className={`h-full ${tone[topic.state] ?? "bg-slate-500"}`} style={{ width: `${topic.mastery_score}%` }} /></div><span className="w-11 text-right font-semibold">{topic.mastery_score}%</span></div>
  </div>;
}

export default function Dashboard() {
  const router = useRouter();
  const [course, setCourse] = useState<Course | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [message, setMessage] = useState("Loading your Calculus workspace…");
  const [busy, setBusy] = useState(false);

  const token = typeof window === "undefined" ? "" : localStorage.getItem("aiu_token") ?? "";
  useEffect(() => { void load(); }, []);
  async function load() {
    try {
      const courses = await api<Course[]>("/courses", {}, token);
      if (!courses[0]) { setMessage("No course is assigned to this account."); return; }
      setCourse(courses[0]);
      const latest = await api<Analysis>(`/courses/${courses[0].id}/analyses/latest`, {}, token).catch(() => null);
      setAnalysis(latest); setMessage("");
    } catch { router.replace("/"); }
  }
  async function analyze() {
    if (!course) return;
    setBusy(true); setMessage("Calculating evidence, prerequisite risks, and a learning path…");
    try { setAnalysis(await api<Analysis>(`/courses/${course.id}/analyses`, { method: "POST" }, token)); setMessage(""); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Analysis could not be completed."); }
    finally { setBusy(false); }
  }

  const critical = analysis?.topics.filter((topic) => topic.state === "CRITICAL" || topic.state === "WEAK") ?? [];
  return <main className="mx-auto max-w-6xl p-6 md:p-10">
    <header className="mb-10 flex flex-col justify-between gap-5 md:flex-row md:items-end"><div><p className="text-sm font-semibold uppercase tracking-[.2em] text-cyan-400">AI University · {course?.code ?? ""}</p><h1 className="mt-2 text-4xl font-bold">{course?.title ?? "Calculus"} knowledge map</h1><p className="mt-2 text-slate-400">Evidence first. Recommendations second.</p></div><Button onClick={analyze} disabled={!course || busy}><BrainCircuit className="mr-2 h-4 w-4" />{busy ? "Analyzing…" : "Analyze my knowledge"}</Button></header>
    {message && <p className="mb-5 rounded-lg border border-slate-700 bg-slate-900 p-4 text-slate-300">{message}</p>}
    {!analysis ? <Card className="text-center"><Network className="mx-auto mb-3 h-8 w-8 text-cyan-400" /><h2 className="text-xl font-bold">Your map is ready to be calculated</h2><p className="mt-2 text-slate-400">Run your first analysis to turn your attempts into a learning path.</p></Card> : <>
      <section className="grid gap-4 md:grid-cols-3"><Card><p className="text-sm text-slate-400">Overall mastery</p><p className="mt-2 text-5xl font-bold text-cyan-300">{analysis.overall_mastery}%</p><p className="mt-3 text-xs text-slate-500">Calculated by engine v{analysis.engine_version}</p></Card><Card><p className="text-sm text-slate-400">Needs attention</p><p className="mt-2 text-5xl font-bold text-rose-300">{critical.length}</p><p className="mt-3 text-xs text-slate-500">weak or critical topics</p></Card><Card><p className="text-sm text-slate-400">Next best step</p><p className="mt-2 text-xl font-bold">{analysis.recommendations[0]?.topic_title ?? "Keep practising"}</p><p className="mt-3 text-sm text-slate-400">{analysis.recommendations[0]?.content}</p></Card></section>
      <section className="mt-6 grid gap-6 lg:grid-cols-[1.35fr_.65fr]"><Card><div className="mb-4 flex items-center gap-2"><Activity className="h-5 w-5 text-cyan-400" /><h2 className="text-xl font-bold">Topic mastery</h2></div>{analysis.topics.map((topic) => <TopicRow key={topic.topic_id} topic={topic} />)}</Card><div className="space-y-6"><Card><div className="mb-3 flex items-center gap-2"><AlertTriangle className="h-5 w-5 text-rose-400" /><h2 className="text-xl font-bold">Critical gaps</h2></div>{critical.length ? critical.map((topic) => <div key={topic.topic_id} className="mb-4 last:mb-0"><p className="font-semibold">{topic.topic_title} · {topic.mastery_score}%</p>{topic.evidence.weak_prerequisites?.[0] && <p className="mt-1 text-sm text-slate-400">Likely prerequisite: {topic.evidence.weak_prerequisites[0].topic} ({topic.evidence.weak_prerequisites[0].mastery}%)</p>}</div>) : <p className="text-slate-400">No critical gaps detected.</p>}</Card><Card><h2 className="mb-3 text-xl font-bold">Analysis summary</h2><p className="text-sm leading-6 text-slate-300">{analysis.ai_summary?.summary ?? "A deterministic summary is available after analysis."}</p><button className="mt-4 inline-flex items-center text-sm font-semibold text-cyan-300" onClick={analyze}>Refresh evidence <ArrowRight className="ml-1 h-4 w-4" /></button></Card></div></section>
    </>}
  </main>;
}
