/* eslint-disable @next/next/no-img-element */

"use client";

import { useState } from "react";

import type { Recommendation } from "@/lib/api";
import { SearchForm } from "@/app/components/SearchForm";

export default function Home() {
  const [summary, setSummary] = useState<string[]>([]);
  const [relaxations, setRelaxations] = useState<string[]>([]);
  const [recs, setRecs] = useState<Recommendation[]>([]);

  return (
    <div className="min-h-dvh bg-zinc-950 text-zinc-50">
      <header className="mx-auto max-w-6xl px-4 py-5">
        <div className="flex items-center justify-between">
          <div className="font-semibold tracking-tight">CulinaryConcierge</div>
          <nav className="text-sm text-zinc-300">
            <a className="hover:text-white" href="#search">
              Home
            </a>
            <span className="mx-3 text-zinc-600">|</span>
            <a className="hover:text-white" href="#results">
              Results
            </a>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 pb-14">
        <section
          id="search"
          className="relative overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-br from-zinc-900 via-zinc-900 to-zinc-800"
        >
          <div className="absolute inset-0 opacity-25">
            <img
              alt=""
              src="https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=1600&q=60"
              className="h-full w-full object-cover"
            />
          </div>
          <div className="relative px-6 py-14 md:px-14">
            <div className="max-w-xl rounded-2xl border border-white/10 bg-zinc-950/55 p-6 backdrop-blur">
              <h1 className="text-2xl font-semibold leading-tight">
                Find Your Perfect Meal with Zomato AI
              </h1>
              <p className="mt-2 text-sm text-zinc-300">
                Select a city + locality, set a budget, and we’ll recommend top
                picks with explanations.
              </p>
              <p className="mt-1 text-xs text-zinc-500">
                📊 12,000+ restaurants in Bangalore area
              </p>

              <SearchForm
                onResults={({ recommendations, relaxationsApplied, summary }) => {
                  setRecs(recommendations);
                  setRelaxations(relaxationsApplied);
                  setSummary(summary);
                  const el = document.getElementById("results");
                  if (el) el.scrollIntoView({ behavior: "smooth" });
                }}
              />
            </div>
          </div>
        </section>

        <section id="results" className="mt-10 grid gap-6 md:grid-cols-12">
          <aside className="md:col-span-4">
            <div className="rounded-2xl border border-white/10 bg-zinc-900 p-4">
              <div className="text-sm font-semibold">AI Reasoning</div>
              <div className="mt-2 space-y-2 text-sm text-zinc-300">
                <div className="rounded-xl border border-white/10 bg-zinc-950/40 p-3">
                  <div className="text-xs uppercase text-zinc-400">
                    Filters
                  </div>
                  <div className="mt-1">
                    {summary.length ? (
                      summary.map((s) => <div key={s}>{s}</div>)
                    ) : (
                      <div>Run a search to see applied filters.</div>
                    )}
                  </div>
                </div>
                <div className="rounded-xl border border-white/10 bg-zinc-950/40 p-3">
                  <div className="text-xs uppercase text-zinc-400">
                    Relaxations
                  </div>
                  <div className="mt-1">
                    {relaxations.length ? (
                      <ul className="list-disc pl-5">
                        {relaxations.map((x) => (
                          <li key={x}>{x}</li>
                        ))}
                      </ul>
                    ) : (
                      <div>None</div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </aside>

          <div className="md:col-span-8">
            <div className="mb-3 flex items-center justify-between">
              <div className="text-sm text-zinc-300">
                Personalized picks for you
              </div>
              <div className="text-xs text-zinc-500">Demo cards</div>
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {(recs.length ? recs : []).map((r, i) => (
                <div
                  key={r.restaurant_id}
                  className="overflow-hidden rounded-2xl border border-white/10 bg-zinc-900"
                >
                  <div className="h-36 bg-zinc-800">
                    <img
                      alt=""
                      src={`https://images.unsplash.com/photo-1552566626-52f8b828add9?auto=format&fit=crop&w=1200&q=60&sig=${i}`}
                      className="h-full w-full object-cover opacity-90"
                    />
                  </div>
                  <div className="p-4">
                    <div className="text-sm font-semibold">
                      {r.rank}. {r.restaurant_name}
                    </div>
                    <div className="mt-1 flex flex-wrap gap-2 text-xs text-zinc-300">
                      <span className="rounded-full border border-white/10 bg-zinc-950/40 px-2 py-0.5">
                        {r.cuisine || "Cuisine"}
                      </span>
                      <span className="rounded-full border border-white/10 bg-zinc-950/40 px-2 py-0.5">
                        Cost: {r.estimated_cost_inr ?? "N/A"}
                      </span>
                      <span className="rounded-full border border-white/10 bg-zinc-950/40 px-2 py-0.5">
                        Rating: {r.rating ?? "N/A"}
                      </span>
                    </div>
                    <div className="mt-2 text-xs text-zinc-300">
                      {r.explanation}
                    </div>
                    <button className="mt-3 w-full rounded-xl bg-red-600 px-3 py-2 text-xs font-semibold hover:bg-red-500">
                      View details
                    </button>
                  </div>
                </div>
              ))}
              {!recs.length ? (
                <div className="rounded-2xl border border-white/10 bg-zinc-900 p-4 text-sm text-zinc-300 md:col-span-2">
                  Run a search to see recommendations here.
                </div>
              ) : null}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
