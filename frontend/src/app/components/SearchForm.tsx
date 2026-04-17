"use client";

import { useEffect, useMemo, useState } from "react";

import {
  getLocalities,
  getLocations,
  postRecommendations,
  type Recommendation,
} from "@/lib/api";

type Props = {
  onResults: (args: {
    recommendations: Recommendation[];
    relaxationsApplied: string[];
    summary: string[];
  }) => void;
};

export function SearchForm({ onResults }: Props) {
  const [locations, setLocations] = useState<string[]>([]);
  const [localities, setLocalities] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>("");

  const [location, setLocation] = useState("Bangalore");
  const [locality, setLocality] = useState("");
  const [budgetMaxInr, setBudgetMaxInr] = useState(1500);
  const [cuisinesRaw, setCuisinesRaw] = useState("Italian,Chinese");
  const [rating, setRating] = useState(0);
  const [topN, setTopN] = useState(10);
  const [additional, setAdditional] = useState("");

  const cuisines = useMemo(
    () =>
      cuisinesRaw
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
    [cuisinesRaw],
  );

  useEffect(() => {
    getLocations()
      .then(setLocations)
      .catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    if (!location.trim()) {
      setLocalities([]);
      return;
    }
    getLocalities(location.trim())
      .then(setLocalities)
      .catch(() => setLocalities([]));
  }, [location]);

  async function submit() {
    setError("");
    if (!location.trim()) {
      setError("Please select a location.");
      return;
    }
    if (budgetMaxInr <= 0) {
      setError("Budget must be > 0.");
      return;
    }
    if (!cuisines.length) {
      setError("Please enter at least one cuisine.");
      return;
    }

    setLoading(true);
    try {
      const data = await postRecommendations({
        location: location.trim(),
        locality: locality.trim() || null,
        budget_max_inr: budgetMaxInr,
        cuisines,
        min_rating: rating,
        additional_preferences: additional.trim() || null,
        top_n: topN,
      });

      onResults({
        recommendations: data.recommendations,
        relaxationsApplied: data.relaxations_applied || [],
        summary: [
          `Location: ${location.trim()}`,
          locality.trim() ? `Locality: ${locality.trim()}` : "Locality: (any)",
          `Budget: ≤ ${budgetMaxInr} INR`,
          `Cuisines: ${cuisines.join(", ")}`,
          `Rating: ${rating}`,
        ],
      });
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mt-5 flex flex-col gap-3">
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <label className="text-xs text-zinc-300">
          City / Area (e.g., Bangalore, Whitefield)
          <input
            list="locations"
            className="mt-1 w-full rounded-xl border border-white/10 bg-zinc-900/60 px-3 py-2 text-sm outline-none focus:border-white/20"
            placeholder="Type city or area name..."
            value={location}
            onChange={(e) => {
              setLocation(e.target.value);
              setLocality("");
            }}
          />
          <datalist id="locations">
            {locations.map((x) => (
              <option key={x} value={x} />
            ))}
          </datalist>
        </label>

        <label className="text-xs text-zinc-300">
          Neighborhood (optional, within selected area)
          <input
            list="localities"
            className="mt-1 w-full rounded-xl border border-white/10 bg-zinc-900/60 px-3 py-2 text-sm outline-none focus:border-white/20"
            placeholder="Select specific neighborhood..."
            value={locality}
            onChange={(e) => setLocality(e.target.value)}
          />
          <datalist id="localities">
            {localities.map((x) => (
              <option key={x} value={x} />
            ))}
          </datalist>
        </label>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <label className="text-xs text-zinc-300">
          Budget max (INR)
          <input
            className="mt-1 w-full rounded-xl border border-white/10 bg-zinc-900/60 px-3 py-2 text-sm outline-none focus:border-white/20"
            type="number"
            min={1}
            step={1}
            value={budgetMaxInr}
            onChange={(e) => setBudgetMaxInr(Number(e.target.value))}
          />
        </label>

        <label className="text-xs text-zinc-300">
          Cuisines (comma-separated)
          <input
            className="mt-1 w-full rounded-xl border border-white/10 bg-zinc-900/60 px-3 py-2 text-sm outline-none focus:border-white/20"
            value={cuisinesRaw}
            onChange={(e) => setCuisinesRaw(e.target.value)}
          />
        </label>

        <label className="text-xs text-zinc-300">
          Rating (0-5)
          <input
            className="mt-1 w-full rounded-xl border border-white/10 bg-zinc-900/60 px-3 py-2 text-sm outline-none focus:border-white/20"
            type="number"
            min={0}
            max={5}
            step={0.5}
            value={rating}
            onChange={(e) => setRating(Number(e.target.value))}
          />
        </label>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <label className="text-xs text-zinc-300 md:col-span-1">
          Number of results to show
          <input
            className="mt-1 w-full rounded-xl border border-white/10 bg-zinc-900/60 px-3 py-2 text-sm outline-none focus:border-white/20"
            type="number"
            min={1}
            max={50}
            step={1}
            value={topN}
            onChange={(e) => setTopN(Number(e.target.value))}
          />
        </label>

        <label className="text-xs text-zinc-300 md:col-span-2">
          Additional preferences (optional)
          <input
            className="mt-1 w-full rounded-xl border border-white/10 bg-zinc-900/60 px-3 py-2 text-sm outline-none focus:border-white/20"
            value={additional}
            onChange={(e) => setAdditional(e.target.value)}
            placeholder="e.g. family-friendly, quick service"
          />
        </label>
      </div>

      <button
        onClick={submit}
        disabled={loading}
        className="mt-1 rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold hover:bg-red-500 disabled:opacity-60"
      >
        {loading ? "Loading..." : "Get Recommendations"}
      </button>

      {error ? <div className="text-sm text-red-300">{error}</div> : null}
    </div>
  );
}

