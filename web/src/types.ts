// Shapes of the API's answers (see app/server.py). Money always arrives as ready-made strings
// ("$1,300.00"): the page never converts cents itself.

export type Verification = {
  group: string;
  status: "valid" | "expired" | "missing";
  verified_on: string;
  expires_on: string;
};
export type Identity = { member_id: string; display_name: string; verifications: Verification[] };

export type DemoMember = {
  id: string;
  display_name: string;
  verifications: { group: string; status: string }[];
};

export type Offer = {
  offer_id: string;
  type: "group_discount" | "cash_back";
  headline_bps: number;
  headline_label: string;
  groups: string[];
  excluded_items: string[];
  annual_cap_cents: number | null;
  annual_cap_dollars: string | null;
  stackable_with_cash_back: boolean;
  expires_on: string | null;
  eligible: boolean;
  reasons: string[];
  reason_text: string[];
};
export type StoreMatches = {
  store_id: string;
  name: string;
  blurb: string;
  category: string;
  art: string | null; // which built-in illustration to draw
  image: string | null; // a licensed photo you added under web/public/stores/ (see docs/IMAGES.md)
  image_credit: string | null;
  offers: Offer[];
};
export type Discounts = { as_of: string; stores: StoreMatches[] };

export type Estimate = {
  store_id: string;
  as_of: string;
  assumptions: string[];
  dollars: { cart: string; group_discount: string; you_pay: string; cash_back: string; total_savings: string };
};

export type Health = {
  ok: boolean;
  assistant: { provider: string | null; model: string | null; configured: boolean };
};
