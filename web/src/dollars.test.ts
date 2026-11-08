import { describe, expect, it } from "vitest";
import { MAX_CART_CENTS, parseDollarsToCents } from "./dollars";

describe("parseDollarsToCents", () => {
  it.each([
    ["200", 20000],
    ["$200", 20000],
    ["  $ 200  ", 20000],
    ["1,500", 150000],
    ["$1,500.00", 150000],
    ["12.5", 1250],
    ["12.50", 1250],
    ["0.05", 5],
    [".5", 50],
    ["$999,999.99", 99_999_999],
    ["1000000", 100_000_000],
  ])("reads %j as %i cents", (text, cents) => {
    expect(parseDollarsToCents(text)).toBe(cents);
  });

  it.each([
    "", "  ", "0", "0.00", "-5", "-$5", "+5", "abc", "1e3", "12.345", "1,00", "1,5000", "1.2.3",
    "$", ".", "1000000.01", "1,234,567.89", "9999999999999999999", "٣", "１２", "12 34", "1_000", "NaN", "Infinity",
  ])("rejects %j", (text) => {
    expect(parseDollarsToCents(text)).toBeNull();
  });

  it("is exact where floating point is not", () => {
    // 0.07 * 100 === 7.000000000000001 and 1.15 * 100 === 114.99999999999999 with floats
    expect(parseDollarsToCents("0.07")).toBe(7);
    expect(parseDollarsToCents("1.15")).toBe(115);
    expect(parseDollarsToCents("19.99")).toBe(1999);
    expect(parseDollarsToCents("0.29")).toBe(29);
  });

  it("uses the same upper limit as the server ($1,000,000.00)", () => {
    expect(MAX_CART_CENTS).toBe(100_000_000);
  });
});
