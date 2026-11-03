// KDP paperback printing costs and royalty rules.
// Source: KDP Help "Printing cost" (G201834340) and "Paperback royalty" (G201834330).
// Last verified: 2026-10-29. Amazon changes these: re-check the source pages before relying on them.
export const PRICING_SOURCE = {
  verified: "2026-10-29",
  printing: "https://kdp.amazon.com/en_US/help/topic/G201834340",
  royalty: "https://kdp.amazon.com/en_US/help/topic/G201834330",
};

// [fixed, perPage] by marketplace / ink / page band / trim class
const COST = {
  USD: {
    black:    { short: { max: 110, regular: [2.30, 0], large: [2.84, 0] }, long: { regular: [1.00, 0.012], large: [1.00, 0.017] } },
    standard: { long: { regular: [1.00, 0.0255], large: [1.00, 0.0402] } },
    premium:  { short: { max: 40, regular: [3.60, 0], large: [4.20, 0] }, long: { regular: [1.00, 0.065], large: [1.00, 0.08] } },
  },
  GBP: {
    black:    { short: { max: 110, regular: [1.93, 0], large: [2.15, 0] }, long: { regular: [0.85, 0.010], large: [0.85, 0.012] } },
    standard: { long: { regular: [0.85, 0.020], large: [0.85, 0.027] } },
    premium:  { short: { max: 40, regular: [2.59, 0], large: [3.24, 0] }, long: { regular: [0.85, 0.0435], large: [0.85, 0.0598] } },
  },
  EUR: {
    black:    { short: { max: 110, regular: [2.05, 0], large: [2.48, 0] }, long: { regular: [0.75, 0.012], large: [0.75, 0.016] } },
    standard: { long: { regular: [0.75, 0.024], large: [0.75, 0.035] } },
    premium:  { short: { max: 40, regular: [2.85, 0], large: [3.61, 0] }, long: { regular: [0.75, 0.0525], large: [0.75, 0.0715] } },
  },
};

// list price at or above which the 60% rate applies (below it: 50%)
const RATE60_FROM = { USD: 9.99, GBP: 7.99, EUR: 9.99 };
export const SYMBOL = { USD: "$", GBP: "£", EUR: "€" };
export const MARKET = { USD: "Amazon.com", GBP: "Amazon.co.uk", EUR: "Amazon.de / EU" };

export const inkForPaper = (paper) =>
  paper === "premium_color" ? "premium" : paper === "standard_color" ? "standard" : "black";

// KDP "large trim": wider than 6.12 in or taller than 9 in
export const isLarge = (trim) => {
  const [w, h] = trim.split("x").map(Number);
  return w > 6.12 || h > 9;
};

export function printingCost(currency, ink, pages, large) {
  if (ink === "standard" && (pages < 72 || pages > 600)) return { error: "Standard color needs 72–600 pages" };
  if (pages < 24 || pages > 828) return { error: "KDP paperbacks need 24–828 pages" };
  const table = COST[currency][ink];
  const band = table.short && pages <= table.short.max ? table.short : table.long;
  const [fixed, per] = band[large ? "large" : "regular"];
  return { cost: fixed + per * pages };
}

const r2 = (x) => Math.round(x * 100) / 100;

export function royalty({ currency, ink, pages, large, price }) {
  const pc = printingCost(currency, ink, pages, large);
  if (pc.error) return pc;
  const threshold = RATE60_FROM[currency];
  const rate = price >= threshold ? 0.6 : 0.5;
  const at50 = pc.cost / 0.5;
  const minPrice = at50 < threshold ? at50 : Math.max(pc.cost / 0.6, threshold);
  return {
    printing: r2(pc.cost),
    rate,
    amazon: r2(rate * price - pc.cost),
    expanded: r2(0.4 * price - pc.cost),
    minPrice: Math.ceil(minPrice * 100) / 100,
    minExpanded: Math.ceil((pc.cost / 0.4) * 100) / 100,
    threshold,
  };
}
