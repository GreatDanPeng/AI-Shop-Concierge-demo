# Store pictures

Every store tile and store page shows a picture. Nothing is downloaded or scraped: by default the page draws an **original illustration** in code (a tent, headphones, books, a sneaker, a lamp, a laptop), coloured from the design tokens so it works in light and dark.

## Using your own photo

If you have a photo you are allowed to use, it replaces the illustration for that store.

1. Put the file in `web/public/stores/`, for example `web/public/stores/s1.jpg`. A 16:10 crop around 1280×800 works well; keep it under about 300 KB. Allowed types: jpg, jpeg, png, webp, avif.
2. In `data/stores.json`, set two fields on that store:
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
- Not brand logos, and not product photos you do not hold the rights to. The demo's stores are fictional (the README says so); using a real brand's photos would suggest the brand is involved.
- This project has a "no scraping" rule (`CLAUDE.md`), so there is no script that fetches pictures from other sites.

## Notes

- The picture is decorative (`alt=""`): the store's name is written next to it, so a screen reader does not read it twice.
- A real product catalogue with product photos is a later milestone (see `docs/PLAN.md`, M3 and M4).
