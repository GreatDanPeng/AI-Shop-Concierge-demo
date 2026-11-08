import { useEffect, useState, type ReactNode } from "react";

// A store's picture. By default an original illustration drawn here in code (no downloaded or scraped
// images). If the store has a licensed photo you added yourself (docs/IMAGES.md), that is shown instead,
// with its credit, and the illustration comes back if the photo cannot be loaded.
// Colours come from tokens through the art-* classes (see art.css), never from attributes.

const ILLUSTRATIONS: Record<string, ReactNode> = {
  tent: (<>
    <path className="art-c" d="M0 84 L38 42 L62 66 L90 30 L132 84 Z" />
    <path className="art-a" d="M50 84 L80 38 L110 84 Z" />
    <path className="art-b" d="M80 38 L80 84 L66 84 Z" />
    <path className="art-line" d="M72 84 L80 64 L88 84" />
    <line className="art-line" x1="18" y1="84" x2="142" y2="84" />
  </>),
  headphones: (<>
    <path className="art-line" d="M40 64 C40 28 120 28 120 64" />
    <rect className="art-a" x="30" y="56" width="20" height="32" rx="9" />
    <rect className="art-a" x="110" y="56" width="20" height="32" rx="9" />
    <rect className="art-b" x="35" y="64" width="10" height="16" rx="5" />
    <rect className="art-b" x="115" y="64" width="10" height="16" rx="5" />
  </>),
  books: (<>
    <rect className="art-a" x="38" y="64" width="84" height="16" rx="3" />
    <rect className="art-b" x="46" y="48" width="70" height="16" rx="3" />
    <rect className="art-c" x="40" y="32" width="76" height="16" rx="3" />
    <line className="art-line" x1="50" y1="72" x2="110" y2="72" />
    <line className="art-line" x1="56" y1="56" x2="104" y2="56" />
    <line className="art-line" x1="52" y1="40" x2="104" y2="40" />
  </>),
  sneaker: (<>
    <path className="art-a" d="M30 72 L30 52 C44 54 52 46 60 36 L74 44 C84 50 98 52 124 60 C136 64 136 72 124 72 Z" />
    <rect className="art-b" x="28" y="70" width="110" height="10" rx="5" />
    <path className="art-line" d="M64 44 L72 52 M72 40 L80 48 M80 46 L88 54" />
    <path className="art-line" d="M30 62 L52 62" />
  </>),
  lamp: (<>
    <path className="art-b" d="M56 26 L104 26 L118 58 L42 58 Z" />
    <line className="art-line" x1="80" y1="58" x2="80" y2="84" />
    <ellipse className="art-a" cx="80" cy="86" rx="24" ry="6" />
    <path className="art-line" d="M56 26 L104 26" />
  </>),
  laptop: (<>
    <rect className="art-a" x="42" y="24" width="76" height="48" rx="5" />
    <rect className="art-c" x="48" y="30" width="64" height="36" rx="2" />
    <path className="art-b" d="M28 76 L132 76 L124 86 L36 86 Z" />
    <line className="art-line" x1="70" y1="81" x2="90" y2="81" />
  </>),
  bag: (<>
    <rect className="art-a" x="52" y="38" width="56" height="46" rx="6" />
    <path className="art-line" d="M64 46 C64 28 96 28 96 46" />
    <line className="art-line" x1="52" y1="52" x2="108" y2="52" />
  </>),
};

export type StoreArtProps = { art: string | null; image: string | null; credit: string | null };

export function StoreArt({ art, image, credit }: StoreArtProps) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [image]); // a new photo gets a fresh try

  if (image && !failed) {
    return (
      <div className="store-art">
        <img src={image} alt="" loading="lazy" onError={() => setFailed(true)} />
        {credit && <small className="art-credit">Photo: {credit}</small>}
      </div>
    );
  }
  const key = art && art in ILLUSTRATIONS ? art : "bag";
  return (
    <div className="store-art">
      <svg viewBox="0 0 160 100" data-art={key} aria-hidden="true" focusable="false" preserveAspectRatio="xMidYMid slice">
        {ILLUSTRATIONS[key]}
      </svg>
    </div>
  );
}
