// Reads a dollar amount typed by a person ("$1,500", "12.5") into integer cents, with integer
// math only (0.07 * 100 is 7.000000000000001 in floating point). Returns null when the text is
// not a clear positive amount within the same limit the server enforces.

export const MAX_CART_CENTS = 100_000_000; // $1,000,000.00, the server's limit

// optional $, then 1,234 / 1234 with up to two decimals, or just .5
const AMOUNT = /^\$?\s*(?:(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d{1,2}))?|\.(\d{1,2}))$/;

export function parseDollarsToCents(text: string): number | null {
  const match = AMOUNT.exec(text.trim());
  if (!match) return null;
  const whole = (match[1] ?? "0").replaceAll(",", "");
  if (whole.length > 9) return null; // far above the limit; also keeps Number() exact
  const fraction = (match[2] ?? match[3] ?? "").padEnd(2, "0");
  const cents = Number(whole) * 100 + Number(fraction || "0");
  return cents > 0 && cents <= MAX_CART_CENTS ? cents : null;
}
