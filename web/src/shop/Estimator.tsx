import { useId, useState, type FormEvent } from "react";
import { parseDollarsToCents } from "../dollars";
import { describeError } from "../errors";
import type { Estimate } from "../types";
import type { ShopApi } from "./useShopData";

export function Estimator({ storeId, api }: { storeId: string; api: Pick<ShopApi, "estimate"> }) {
  const [text, setText] = useState("");
  const [result, setResult] = useState<Estimate | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const inputId = useId();

  async function run(event: FormEvent) {
    event.preventDefault();
    const cents = parseDollarsToCents(text);
    if (cents === null) {
      setResult(null);
      setProblem("Enter an amount like 200 or $1,500.00 (up to $1,000,000).");
      return;
    }
    setProblem(null);
    setBusy(true);
    try {
      setResult(await api.estimate(storeId, cents));
    } catch (error) {
      setResult(null);
      setProblem(describeError(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="estimator" onSubmit={run}>
      <h2>Estimate a cart</h2>
      <label htmlFor={inputId}>Cart total ($)</label>
      <div className="estimator-row">
        <input id={inputId} inputMode="decimal" placeholder="200" value={text} onChange={(e) => setText(e.target.value)} />
        <button type="submit" className="button" disabled={busy}>Estimate</button>
      </div>
      {problem && <p className="error" role="alert">{problem}</p>}
      {result && (
        <>
          <dl className="result">
            <dt>Cart</dt><dd>{result.dollars.cart}</dd>
            <dt>Group discount</dt><dd>{result.dollars.group_discount}</dd>
            <dt>Cash back</dt><dd>{result.dollars.cash_back}</dd>
            <dt>You pay</dt><dd className="strong">{result.dollars.you_pay}</dd>
            <dt>You save</dt><dd>{result.dollars.total_savings}</dd>
          </dl>
          <p className="fine-print">
            As of {result.as_of}. Offers can change at any time; this is an estimate with no guarantee.
          </p>
        </>
      )}
    </form>
  );
}
