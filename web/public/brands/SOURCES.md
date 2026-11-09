# Brand logos: where each file came from

These are the **trademarks of their respective owners**. They appear only to identify a brand on an
**invented** demo offer, for personal learning and technical practice, never commercially. See the
Disclaimer at the top of the README. No brand is involved in this project or endorses it.

A disclaimer is not permission. Check each brand's own logo guidelines before using this project anywhere
else, and if a brand objects, set that store's `logo` to `null` in `data/brand_stores.json` (its illustration
comes back) and delete the file. Samsung publishes its rules at
https://www.samsung.com/us/about-us/brand-identity/logo/.

Retrieved 2026-11-08. Files are used as downloaded except where "Changes" says otherwise.

| File | Brand | Source | Licence tag at the source | Changes |
| --- | --- | --- | --- | --- |
| `apple.svg` | Apple | https://raw.githubusercontent.com/simple-icons/simple-icons/16.37.0/icons/apple.svg | CC0 1.0 (Simple Icons project licence, `SIMPLE_ICONS_LICENSE.md`) | `fill="#000000"` added |
| `samsung.svg` | Samsung | https://raw.githubusercontent.com/simple-icons/simple-icons/16.37.0/icons/samsung.svg | CC0 1.0 (Simple Icons project licence) | `fill="#1428A0"` added |
| `nike.svg` | Nike | https://raw.githubusercontent.com/simple-icons/simple-icons/16.37.0/icons/nike.svg | CC0 1.0 (Simple Icons project licence) | `fill="#111111"` added |
| `thenorthface.svg` | The North Face | https://raw.githubusercontent.com/simple-icons/simple-icons/16.37.0/icons/thenorthface.svg | CC0 1.0 (Simple Icons project licence) | `fill="#000000"` added |
| `ikea.svg` | IKEA | https://raw.githubusercontent.com/simple-icons/simple-icons/16.37.0/icons/ikea.svg | CC0 1.0 (Simple Icons project licence) | `fill="#0058A3"` added |
| `marriott.svg` | Marriott | https://raw.githubusercontent.com/simple-icons/simple-icons/16.37.0/icons/marriott.svg | CC0 1.0 (Simple Icons project licence) | `fill="#A70023"` added |
| `bestbuy.svg` | Best Buy | https://upload.wikimedia.org/wikipedia/commons/c/c4/Best_Buy_logo_2018.svg (File:Best Buy logo 2018.svg) | Public domain (Wikimedia Commons tag; marked trademarked) | none |
| `lululemon.svg` | lululemon | https://upload.wikimedia.org/wikipedia/commons/2/22/Lululemon_Athletica_logo.svg (File:Lululemon Athletica logo.svg) | Public domain (Wikimedia Commons tag; marked trademarked) | none |
| `levis.svg` | Levi's | https://upload.wikimedia.org/wikipedia/commons/7/75/Levi%27s_logo.svg (File:Levi's logo.svg) | Public domain (Wikimedia Commons tag; marked trademarked) | none |
| `homedepot.svg` | The Home Depot | https://upload.wikimedia.org/wikipedia/commons/f/f6/The_Home_Depot_logo.svg (File:The Home Depot logo.svg) | Public domain (Wikimedia Commons tag; marked trademarked) | none |
| `barnesandnoble.svg` | Barnes & Noble | https://upload.wikimedia.org/wikipedia/commons/2/2c/Barnes_%26_Noble_logo_%282021%29.svg (File:Barnes & Noble logo (2021).svg) | Public domain (Wikimedia Commons tag; marked trademarked) | none |
| `hertz.svg` | Hertz | https://upload.wikimedia.org/wikipedia/commons/8/8f/Hertz_Logo.svg (File:Hertz Logo.svg) | Public domain (Wikimedia Commons tag; marked trademarked) | the standard W3C `<!DOCTYPE ...>` line removed |

## What the licence tags mean

- **Simple Icons** releases its project under CC0, but its own disclaimer says that does not make every icon
  free of other rights: check each icon's licence and the brand's guidelines, and brands may ask for removal.
- **Wikimedia Commons** tags these logos "Public domain" because the artwork is too simple to carry a
  copyright. Commons also marks them "trademarked": the trademark rights stay with the owner.

## REI has no logo here

REI's logo is not available as a free file (it only exists on Wikipedia as a restricted "fair use" upload),
so the REI store keeps its original illustration. To add it, put a logo file you are allowed to use in this
folder (for example `rei.svg`), set `"logo": "/brands/rei.svg"` for REI in `data/brand_stores.json`, list it
in the table above, and add REI to the Disclaimer in the README. `tests/test_brand_logos.py` checks every
step.

## Every file is inspected

`tests/test_brand_logos.py` rejects any SVG here that contains a script, an outside link, an image, text
(which would depend on fonts), an event handler, or a stylesheet or `<use>` that points outside the file.
