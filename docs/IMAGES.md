# Store pictures

Every store tile and store page shows a picture, chosen in this order: a **licensed photo** you added (below), then the brand's own **logo** (every brand store has one), then an **original illustration** drawn in code from the design tokens, so it works in light and dark. The six original stores have a tent, headphones, books, a sneaker, a lamp and a laptop; each brand store also has its own everyday object (devices, a phone, a TV, a yoga mat and top, jeans, a running shoe, a backpack, a jacket, a sofa, a toolbox, an open book, a hotel, a car), which is the fallback when its logo cannot load. Illustrations show objects only: no logos and no brand marks.

## Brand logos

Logos are small SVG files in `web/public/brands/`, named by a store's `logo` field in `data/brand_stores.json` (for example `"logo": "/brands/apple.svg"`; `null` shows the illustration). They are shown contained, never cropped, on a white plate that stays white in dark mode, because official logos are made for light backgrounds. `web/public/brands/SOURCES.md` records, for every file, its source address, its licence tag and any change I made.

- Six come from Simple Icons (CC0 project) and six from Wikimedia Commons (tagged public domain, marked trademarked). REI was dropped from the demo because its logo is not available as a free file.
- **They are the owners' trademarks.** The README Disclaimer says so, and `tests/test_readme_disclaimer.py` fails if a logo is shown whose brand is not named there. A disclaimer is not permission: check each brand's own guidelines before using the project anywhere else, and if a brand objects, set its `logo` to `null` and delete the file.
- **To add or replace a logo:** put the SVG in `web/public/brands/`, set the store's `logo`, add a row to `SOURCES.md`, add the brand to the Disclaimer, then run `pytest tests/test_brand_logos.py tests/test_readme_disclaimer.py`. That checks the path, that the file exists, that it has no script, outside link, image, text or event handler, and that it is small.
- Logos are never fetched while the app runs, and there is no script that downloads them.

## Using your own photo

If you have a photo you are allowed to use, it replaces the illustration for that store.

1. Put the file in `web/public/stores/`, for example `web/public/stores/s1.jpg`. A 16:10 crop around 1280×800 works well; keep it under about 300 KB. Allowed types: jpg, jpeg, png, webp, avif.
2. In `data/stores.json` (or `data/brand_stores.json` for a brand store), set two fields on that store:
   ```json
   "image": "/stores/s1.jpg",
   "image_credit": "Jane Doe, CC BY 4.0"
   ```
   The credit line is required whenever there is a photo; it is shown on the picture as "Photo: …".
3. Rebuild the page: `cd web && npm run build`.
4. Run `pytest tests/test_store_fields.py`. It checks the path (only `/stores/<name>.<type>`, no web addresses, no `..`) and that a credit is present.

If the file is missing or cannot be loaded, the illustration comes back by itself.

## What is safe to use

- Photos you took, or that are licensed for this use. Read the licence: many need the credit line above.
- Not brand photos, and not logos other than the ones recorded in `web/public/brands/SOURCES.md`. The demo's offers are invented (the README says so), and a real logo or official product photo next to an invented offer can look official; keep the Disclaimer, the footer and the store descriptions in place.
- This project has a "no scraping" rule (`CLAUDE.md`), so there is no script that fetches pictures from other sites.

## Notes

- The picture, logo or illustration, is decorative (`alt=""`): the store's name is written next to it, so a screen reader does not read it twice.
- A real product catalogue with product photos is a later milestone (see `docs/PLAN.md`, M3 and M4).
