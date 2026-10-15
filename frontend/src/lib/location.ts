export const COUNTRIES = [{ region: "india", name: "India" }, { region: "us", name: "United States" }] as const;

// Explicit search preferences take priority over the resume home address.
export function locationRegion(location: string): "india" | "us" | undefined {
  const text = location.toLowerCase().replace(/\./g, "").trim();
  if (/\b(india|in|bharat|mumbai|delhi|bengaluru|bangalore|hyderabad|pune|chennai|gurugram|gurgaon|noida|kolkata)\b/.test(text)) return "india";
  if (/\b(us|usa|united states(?: of america)?|new york|san francisco|seattle|boston|austin|chicago|los angeles|san jose|palo alto|mountain view|menlo park|berkeley|oakland|sunnyvale|santa clara|redwood city|cambridge|denver|miami|atlanta|dallas|houston)\b/.test(text)) return "us";
  return undefined;
}
