import type { ClaimType, Verdict } from "../api/types";

export const VERDICTS: Record<Verdict, { label: string; glyph: string; description: string }> = {
  false: { label: "False", glyph: "✕", description: "Higher-ranked sources clearly contradict it." },
  true: { label: "True", glyph: "✓", description: "At least two independent, well-ranked sources confirm it." },
  misleading: { label: "Misleading", glyph: "◐", description: "Partly accurate, but missing context that changes what it means." },
  unverified: { label: "Unverified", glyph: "?", description: "Sources conflict or are too weak to decide. We say so instead of guessing." },
  outdated: { label: "Outdated", glyph: "↻", description: "It was true once, but it isn't any more." },
  opinion: { label: "Not checkable", glyph: "—", description: "An opinion or a prediction. Predictions are checked again when they fall due." },
};

export const VERDICT_ORDER: Verdict[] = ["false", "true", "misleading", "unverified", "outdated", "opinion"];

export const CLAIM_TYPES: Record<ClaimType, string> = {
  verifiable: "Verifiable fact",
  contested: "Contested claim",
  opinion: "Opinion",
  prediction: "Prediction",
};
