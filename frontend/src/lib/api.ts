export type Recommendation = {
  restaurant_id: string;
  restaurant_name: string;
  cuisine: string;
  rating: number | null;
  estimated_cost_inr: number | null;
  rank: number;
  explanation: string;
  match_reasons: string[];
};

export type RecommendationsResponse = {
  recommendations: Recommendation[];
  relaxations_applied: string[];
};

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/+$/, "") ||
  "http://127.0.0.1:8001";

export async function getLocations(): Promise<string[]> {
  const r = await fetch(`${API_BASE}/locations`, { cache: "no-store" });
  if (!r.ok) throw new Error(`locations failed: ${r.status}`);
  return await r.json();
}

export async function getLocalities(location: string): Promise<string[]> {
  const url = new URL(`${API_BASE}/localities`);
  url.searchParams.set("location", location);
  const r = await fetch(url.toString(), { cache: "no-store" });
  if (!r.ok) throw new Error(`localities failed: ${r.status}`);
  return await r.json();
}

export async function postRecommendations(payload: {
  location: string;
  locality?: string | null;
  budget_max_inr: number;
  cuisines: string[];
  min_rating?: number;
  additional_preferences?: string | null;
  top_n?: number;
}): Promise<RecommendationsResponse> {
  const r = await fetch(`${API_BASE}/recommendations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await r.json();
  if (!r.ok) throw new Error(JSON.stringify(data, null, 2));
  return data;
}

