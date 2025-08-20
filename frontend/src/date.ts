// Date/time helpers to ensure backend UTC timestamps are shown in the user's local timezone

// Detect if string has timezone info (Z or "+/-HH:MM")
function hasTimeZonePart(s: string): boolean {
  return /[zZ]|[+-]\d{2}:?\d{2}$/.test(s);
}

// Parse a backend ISO string safely:
// - If it's date-only (YYYY-MM-DD), construct a local Date at midnight to avoid TZ shifting the day
// - If it lacks a timezone but has time, assume UTC by appending Z
export function parseBackendDate(iso?: string | null): Date | null {
  if (!iso) return null;
  const trimmed = iso.trim();
  if (!trimmed) return null;
  // Date-only case
  const m = trimmed.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (m) {
    const y = Number(m[1]);
    const mm = Number(m[2]);
    const d = Number(m[3]);
    // Construct at local midnight so the calendar date stays the same for the viewer
    return new Date(y, mm - 1, d, 0, 0, 0, 0);
  }
  const withTz = hasTimeZonePart(trimmed)
    ? trimmed
    : `${trimmed.replace(/\s+/g, " ")}Z`;
  const d = new Date(withTz);
  if (isNaN(d.getTime())) return null;
  return d;
}

export function formatLocalDate(iso?: string | null, locale?: string): string {
  const d = parseBackendDate(iso);
  if (!d) return "-";
  return d.toLocaleDateString(locale, {
    year: "numeric",
    month: "short",
    day: "2-digit",
  });
}

export function formatLocalDateLong(
  iso?: string | null,
  locale?: string,
): string {
  const d = parseBackendDate(iso);
  if (!d) return "-";
  return d.toLocaleDateString(locale, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export function formatLocalDateTime(
  iso?: string | null,
  locale?: string,
): string {
  const d = parseBackendDate(iso);
  if (!d) return "";
  const currentYear = new Date().getFullYear();
  const opts: Intl.DateTimeFormatOptions = {
    hour: "2-digit",
    minute: "2-digit",
    month: "short",
    day: "2-digit",
  };
  if (d.getFullYear() !== currentYear) opts.year = "numeric";
  return d.toLocaleString(locale, opts);
}
