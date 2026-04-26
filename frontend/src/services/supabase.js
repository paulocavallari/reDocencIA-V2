import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || "";
const supabasePublishableKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY || "";

export const isSupabaseConfigured = Boolean(supabaseUrl && supabasePublishableKey);

export const supabase = isSupabaseConfigured
  ? createClient(supabaseUrl, supabasePublishableKey, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
      },
    })
  : null;

export function getSupabaseProjectRef() {
  if (!supabaseUrl) {
    return null;
  }

  try {
    return new URL(supabaseUrl).hostname.split(".")[0] || null;
  } catch {
    return null;
  }
}

export function maskSupabaseKey(value) {
  if (!value) {
    return "não configurada";
  }
  if (value.length <= 12) {
    return "*".repeat(value.length);
  }
  return `${value.slice(0, 8)}...${value.slice(-6)}`;
}

export function getSupabaseConfig() {
  return {
    url: supabaseUrl || null,
    keyPreview: maskSupabaseKey(supabasePublishableKey),
    projectRef: getSupabaseProjectRef(),
    configured: isSupabaseConfigured,
  };
}