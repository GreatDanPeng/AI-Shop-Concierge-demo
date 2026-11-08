import { Fragment, type ReactNode } from "react";
import { isStoreAddress } from "./links";

// Renders a model's reply as text. The model's words are untrusted, so this never builds HTML from
// them: everything is a React text node (React escapes it), and only these become elements:
// **bold**, "- " bullet lists, paragraph breaks, and links to a store page of this shop, written as
// [label](#/store/<id>). A link is made only when its address passes isStoreAddress (links.ts); any
// other address stays visible text. No images, headings, code, or links anywhere else.

type Block = { kind: "paragraph"; lines: string[] } | { kind: "list"; items: string[] };

const BULLET = /^\s*[-*•]\s+(.*)$/;

function toBlocks(text: string): Block[] {
  const blocks: Block[] = [];
  let paragraph: string[] | null = null;
  let list: string[] | null = null;
  for (const rawLine of text.split("\n")) {
    const line = rawLine.trimEnd();
    if (line.trim() === "") {
      paragraph = null;
      list = null;
      continue;
    }
    const bullet = BULLET.exec(line);
    if (bullet) {
      paragraph = null;
      if (!list) {
        list = [];
        blocks.push({ kind: "list", items: list });
      }
      list.push(bullet[1]);
    } else {
      list = null;
      if (!paragraph) {
        paragraph = [];
        blocks.push({ kind: "paragraph", lines: paragraph });
      }
      paragraph.push(line);
    }
  }
  return blocks;
}

// "[label](address)": the label holds no bracket, parenthesis or line break; the address no space.
const LINK = /\[([^[\]()\n]+)\]\(([^()\s]*)\)/g;

function linkify(text: string, onLink?: () => void): ReactNode {
  const out: ReactNode[] = [];
  let last = 0;
  for (const match of text.matchAll(LINK)) {
    const [whole, label, address] = match;
    if (!isStoreAddress(address)) continue; // not ours: it stays as the text it was written as
    if (match.index > last) out.push(text.slice(last, match.index));
    out.push(
      <a key={match.index} href={address} onClick={onLink}>
        {label}
      </a>,
    );
    last = match.index + whole.length;
  }
  if (last === 0) return text;
  if (last < text.length) out.push(text.slice(last));
  return out;
}

function inline(text: string, onLink?: () => void): ReactNode {
  const parts = text.split("**");
  if (parts.length % 2 === 0) return linkify(text, onLink); // unbalanced markers: text as written
  return parts.map((part, index) => (
    <Fragment key={index}>
      {index % 2 === 1 && part ? <strong>{linkify(part, onLink)}</strong> : linkify(part, onLink)}
    </Fragment>
  ));
}

// onLink runs when a store link is clicked (the browser still follows it); the widget uses it to
// get out of the way on a small screen.
export function ReplyText({ text, onLink }: { text: string; onLink?: () => void }) {
  return (
    <>
      {toBlocks(text).map((block, index) =>
        block.kind === "list" ? (
          <ul key={index}>
            {block.items.map((item, i) => (
              <li key={i}>{inline(item, onLink)}</li>
            ))}
          </ul>
        ) : (
          <p key={index}>
            {block.lines.map((line, i) => (
              <Fragment key={i}>
                {i > 0 && <br />}
                {inline(line, onLink)}
              </Fragment>
            ))}
          </p>
        ),
      )}
    </>
  );
}
