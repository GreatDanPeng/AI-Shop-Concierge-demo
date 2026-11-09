import { useEffect, useState, type ReactNode } from "react";

// A store's picture. In order: a licensed photo you added yourself (docs/IMAGES.md), shown with its credit;
// then the brand's own logo, a file under /brands/ (see web/public/brands/SOURCES.md), shown contained on a
// white plate; then an original illustration drawn here in code. If a photo or logo cannot be loaded, the
// next one down comes back. Illustration colours come from tokens through the art-* classes (see art.css),
// never from attributes.

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
  // ---- the invented brand stores: one everyday object each, no logos and no brand marks ----
  devices: (<>
    <rect className="art-a" x="30" y="28" width="72" height="46" rx="5" />
    <rect className="art-c" x="36" y="34" width="60" height="34" rx="2" />
    <path className="art-b" d="M20 78 L112 78 L106 88 L26 88 Z" />
    <rect className="art-b" x="98" y="44" width="34" height="44" rx="5" />
    <rect className="art-c" x="102" y="49" width="26" height="34" rx="2" />
    <line className="art-line" x1="60" y1="83" x2="74" y2="83" />
  </>),
  phone: (<>
    <rect className="art-a" x="58" y="12" width="44" height="78" rx="9" />
    <rect className="art-c" x="63" y="21" width="34" height="58" rx="3" />
    <line className="art-line" x1="74" y1="16" x2="86" y2="16" />
    <rect className="art-b" x="68" y="29" width="10" height="10" rx="3" />
    <rect className="art-a" x="82" y="29" width="10" height="10" rx="3" />
    <rect className="art-a" x="68" y="44" width="10" height="10" rx="3" />
    <rect className="art-b" x="82" y="44" width="10" height="10" rx="3" />
    <circle className="art-line" cx="80" cy="85" r="2.5" />
  </>),
  tv: (<>
    <rect className="art-a" x="26" y="20" width="108" height="58" rx="5" />
    <rect className="art-c" x="32" y="26" width="96" height="46" rx="2" />
    <circle className="art-b" cx="102" cy="40" r="7" />
    <path className="art-line" d="M32 68 L58 48 L76 60 L92 50 L128 68" />
    <line className="art-line" x1="80" y1="78" x2="80" y2="86" />
    <line className="art-line" x1="58" y1="88" x2="102" y2="88" />
  </>),
  yoga: (<>
    <rect className="art-a" x="22" y="58" width="70" height="26" rx="13" />
    <ellipse className="art-b" cx="92" cy="71" rx="9" ry="13" />
    <path className="art-line" d="M92 66 C97 66 97 76 92 76" />
    <line className="art-line" x1="34" y1="71" x2="76" y2="71" />
    <path className="art-c" d="M104 20 L112 20 C112 32 124 32 124 20 L132 20 L135 84 L101 84 Z" />
    <path className="art-line" d="M106 56 L130 56" />
  </>),
  jeans: (<>
    <path className="art-c" d="M52 14 L108 14 L113 90 L88 90 L80 44 L72 90 L47 90 Z" />
    <rect className="art-a" x="52" y="14" width="56" height="9" rx="2" />
    <line className="art-line" x1="80" y1="23" x2="80" y2="44" />
    <path className="art-line" d="M56 30 C65 30 67 38 62 41" />
    <path className="art-line" d="M104 30 C95 30 93 38 98 41" />
    <circle className="art-b" cx="80" cy="19" r="2.5" />
  </>),
  runner: (<>
    <path className="art-c" d="M26 70 C26 52 40 50 50 48 L66 36 C72 32 80 36 82 42 C88 56 108 56 128 64 C138 68 136 74 126 74 L30 74 C27 74 26 72 26 70 Z" />
    <rect className="art-b" x="26" y="58" width="14" height="16" rx="3" />
    <rect className="art-a" x="22" y="72" width="116" height="14" rx="7" />
    <path className="art-line" d="M30 79 C40 74 48 84 58 79 C68 74 76 84 86 79 C96 74 104 84 114 79 C122 76 128 80 132 79" />
    <line className="art-line" x1="52" y1="60" x2="106" y2="66" />
  </>),
  jacket: (<>
    <path className="art-a" d="M60 18 L100 18 L120 32 L128 76 L112 78 L110 50 L108 88 L52 88 L50 50 L48 78 L32 76 L40 32 Z" />
    <rect className="art-b" x="66" y="11" width="28" height="9" rx="3" />
    <line className="art-line" x1="80" y1="20" x2="80" y2="88" />
    <path className="art-line" d="M52 46 L108 46 M52 64 L108 64" />
  </>),
  sofa: (<>
    <rect className="art-a" x="30" y="38" width="100" height="36" rx="8" />
    <rect className="art-b" x="40" y="54" width="80" height="22" rx="6" />
    <rect className="art-a" x="22" y="48" width="20" height="34" rx="8" />
    <rect className="art-a" x="118" y="48" width="20" height="34" rx="8" />
    <line className="art-line" x1="80" y1="56" x2="80" y2="76" />
    <line className="art-line" x1="36" y1="84" x2="36" y2="92" />
    <line className="art-line" x1="124" y1="84" x2="124" y2="92" />
  </>),
  toolbox: (<>
    <rect className="art-c" x="112" y="26" width="7" height="30" rx="3" />
    <rect className="art-b" x="102" y="18" width="27" height="10" rx="2" />
    <rect className="art-a" x="28" y="48" width="100" height="40" rx="6" />
    <rect className="art-b" x="28" y="48" width="100" height="14" rx="6" />
    <path className="art-line" d="M60 48 L60 38 C60 34 96 34 96 38 L96 48" />
    <line className="art-line" x1="28" y1="62" x2="128" y2="62" />
    <rect className="art-c" x="70" y="58" width="18" height="12" rx="3" />
  </>),
  openbook: (<>
    <path className="art-a" d="M80 30 C66 24 44 24 28 30 L28 80 C44 74 66 74 80 80 Z" />
    <path className="art-c" d="M80 30 C94 24 116 24 132 30 L132 80 C116 74 94 74 80 80 Z" />
    <line className="art-line" x1="80" y1="30" x2="80" y2="80" />
    <path className="art-line" d="M38 42 C50 39 62 39 72 43 M38 52 C50 49 62 49 72 53 M38 62 C50 59 62 59 72 63" />
    <path className="art-line" d="M88 43 C98 39 110 39 122 42 M88 53 C98 49 110 49 122 52" />
    <path className="art-b" d="M104 26 L104 50 L110 44 L116 50 L116 27 Z" />
  </>),
  hotel: (<>
    <rect className="art-a" x="44" y="22" width="72" height="66" rx="4" />
    <path className="art-line" d="M44 22 L80 12 L116 22" />
    <rect className="art-c" x="52" y="30" width="14" height="10" rx="2" />
    <rect className="art-c" x="73" y="30" width="14" height="10" rx="2" />
    <rect className="art-c" x="94" y="30" width="14" height="10" rx="2" />
    <rect className="art-c" x="52" y="46" width="14" height="10" rx="2" />
    <rect className="art-c" x="73" y="46" width="14" height="10" rx="2" />
    <rect className="art-c" x="94" y="46" width="14" height="10" rx="2" />
    <rect className="art-b" x="70" y="62" width="20" height="26" rx="3" />
    <line className="art-line" x1="30" y1="88" x2="130" y2="88" />
  </>),
  car: (<>
    <path className="art-a" d="M24 66 L24 56 C24 52 28 50 32 50 L48 48 L62 34 C64 32 66 31 68 31 L104 31 C108 31 110 32 112 35 L120 48 C132 50 138 54 138 60 L138 66 Z" />
    <path className="art-c" d="M64 48 L72 36 L100 36 L108 48 Z" />
    <line className="art-line" x1="86" y1="36" x2="86" y2="48" />
    <circle className="art-b" cx="52" cy="70" r="12" />
    <circle className="art-b" cx="112" cy="70" r="12" />
    <circle className="art-line" cx="52" cy="70" r="5" />
    <circle className="art-line" cx="112" cy="70" r="5" />
  </>),
  bag: (<>
    <rect className="art-a" x="52" y="38" width="56" height="46" rx="6" />
    <path className="art-line" d="M64 46 C64 28 96 28 96 46" />
    <line className="art-line" x1="52" y1="52" x2="108" y2="52" />
  </>),
};

// Only a plain file under /brands/ is ever loaded as a logo: never an address, a query, or a path that climbs.
const LOGO_PATH = /^\/brands\/[A-Za-z0-9_-]+\.(svg|png|webp)$/;

export type StoreArtProps = { art: string | null; image: string | null; credit: string | null; logo?: string | null };

export function StoreArt({ art, image, credit, logo = null }: StoreArtProps) {
  const [photoFailed, setPhotoFailed] = useState(false);
  const [logoFailed, setLogoFailed] = useState(false);
  useEffect(() => setPhotoFailed(false), [image]); // a new photo gets a fresh try
  useEffect(() => setLogoFailed(false), [logo]); // and so does a new logo

  if (image && !photoFailed) {
    return (
      <div className="store-art">
        <img src={image} alt="" loading="lazy" onError={() => setPhotoFailed(true)} />
        {credit && <small className="art-credit">Photo: {credit}</small>}
      </div>
    );
  }
  if (logo && LOGO_PATH.test(logo) && !logoFailed) {
    return (
      <div className="store-art store-art--logo">
        <img src={logo} alt="" loading="lazy" onError={() => setLogoFailed(true)} />
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
