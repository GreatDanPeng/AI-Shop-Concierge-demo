import type { DemoMember, Offer } from "../types";

export const words = (group: string) => group.replaceAll("_", " ");

export const offerLabel = (offer: Offer) => `${offer.headline_label} ${offer.type === "cash_back" ? "cash back" : "off"}`;

export function memberSummary(member: DemoMember): string {
  if (member.verifications.length === 0) return "no verified group";
  return member.verifications
    .map((v) => (v.status === "valid" ? words(v.group) : `${words(v.group)} (${v.status})`))
    .join(", ");
}
