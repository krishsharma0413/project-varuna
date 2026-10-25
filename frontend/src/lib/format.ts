const relative = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
const dateTime = new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short" });

const STEPS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["year", 31_536_000], ["month", 2_592_000], ["week", 604_800], ["day", 86_400], ["hour", 3600], ["minute", 60],
];

export function timeAgo(iso: string | null | undefined): string {
  if (!iso) return "";
  const seconds = (new Date(iso).getTime() - Date.now()) / 1000;
  for (const [unit, size] of STEPS) {
    if (Math.abs(seconds) >= size) return relative.format(Math.round(seconds / size), unit);
  }
  return "just now";
}

export function formatDate(iso: string | null | undefined): string {
  return iso ? dateTime.format(new Date(iso)) : "";
}

export function duration(seconds: number | null | undefined): string {
  if (!seconds) return "";
  const s = Math.round(seconds);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

export function minutesAgo(iso: string): { value: string; unit: string } {
  const minutes = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60_000));
  if (minutes < 60) return { value: String(minutes), unit: "min ago" };
  if (minutes < 60 * 48) return { value: String(Math.round(minutes / 60)), unit: "hr ago" };
  return { value: String(Math.round(minutes / 1440)), unit: "days ago" };
}

/** Stable pattern index for the placeholder thumbnail of a reel. */
export function patternFor(id: string): number {
  let hash = 0;
  for (const char of id) hash = (hash * 31 + char.charCodeAt(0)) | 0;
  return Math.abs(hash) % 6;
}
