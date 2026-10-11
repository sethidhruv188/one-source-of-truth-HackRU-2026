export const titleCase = (s = "") =>
  s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

export const num = (v) =>
  typeof v === "number" ? v.toLocaleString(undefined, { maximumFractionDigits: 2 }) : v;

export const money = (v) =>
  typeof v === "number"
    ? v.toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 0 })
    : v;

// Columns that should read as a status rather than a bare number.
export function tone(column, value) {
  if (typeof value !== "number") return null;
  if (column === "kits_remaining")       return value < 5 ? "bad" : value < 15 ? "warn" : "good";
  if (column === "days_payment_overdue") return value > 60 ? "bad" : value > 0 ? "warn" : "good";
  if (column === "open_safety_cases")    return value > 6 ? "bad" : value > 0 ? "warn" : "good";
  if (column === "systems_contributing") return value < 5 ? "warn" : "good";
  return null;
}
