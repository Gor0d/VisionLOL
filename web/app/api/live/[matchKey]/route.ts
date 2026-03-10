import { NextRequest, NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

/**
 * GET /api/live/[matchKey]
 * Retorna o estado completo de todos os jogadores de uma partida
 */
export async function GET(
  _req: NextRequest,
  { params }: { params: { matchKey: string } }
) {
  const { data, error } = await supabase
    .from("live_match_state")
    .select("*")
    .eq("match_key", params.matchKey)
    .order("updated_at", { ascending: false });

  if (error) return NextResponse.json({ error: error.message }, { status: 500 });

  return NextResponse.json({ match_key: params.matchKey, players: data ?? [] });
}
