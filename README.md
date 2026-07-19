# Infineon CMSIS SVD collection

Local collection of CMSIS SVD files for Infineon (including former Cypress) MCUs,
pulled from five public Infineon GitHub repos on 2026-07-19. Files are unmodified
copies (provenance: pristine), organized by device family into one folder per
family at the repo root.
Every file was parsed with Python xml.etree and has a `device` root element.

50 files, 89.7 MB.

## Coverage

| Family | Folder | Files | Notes |
|---|---|---|---|
| PSoC 6 | PSoC6 | 4 | psoc6_01 to psoc6_04 |
| PSoC 4 | PSoC4 | 11 | includes PSoC 4 HV (psoc4hv* files) |
| PMG1 | PMG1 | 5 | pmg1b2, pmg1s0..s3 |
| CCG | CCG | 3 | ccg6df_cfp, ccg7d, ccg7s |
| PAG2S | PAG2S | 1 | |
| TRAVEO T2G | TRAVEO | 6 | tviibe1m/2m/4m, tviibh16m, tviic2d4m/2d6m |
| XMC1000 | XMC1000 | 4 | XMC1100 to XMC1400 |
| XMC4000 | XMC4000 | 7 | XMC4100 to XMC4800 |
| XMC5000 | XMC5000 | 3 | xmc5100, xmc5200, xmc5300 |
| XMC7000 | XMC7000 | 2 | cat1c4m, cat1c8m (XMC71xx/XMC72xx) |
| CYW | CYW | 1 | cyw20829 |
| PSC3 | PSC3 | 1 | |
| PSoC Edge | PSE84 | 1 | pse84 |
| AURIX | AURIX | 1 | TC37XPD (TC375), the only public AURIX SVD |

## Sources

All cloned with `git clone --filter=blob:none --depth 1`. HEAD SHAs at fetch time:

| Repo | SHA | Files taken from |
|---|---|---|
| https://github.com/Infineon/mtb-pdl-cat1 | 4a5e192cc76f7fdc8abff42d8dab8e52e199e348 | devices/COMPONENT_CAT1A/svd, COMPONENT_CAT1B/svd, COMPONENT_CAT1C/svd |
| https://github.com/Infineon/mtb-pdl-cat2 | 35f1714623cfea682d5e285af80d50416b4c7bbc | devices/svd |
| https://github.com/Infineon/mtb-xmclib-cat3 | c24888699c6c5cfd6e5475be90d9703e43540d04 | CMSIS/Infineon/COMPONENT_XMC*/SVD |
| https://github.com/Infineon/mtb-dsl-pse8xxgp | c2793cf168c31420266648473122d78897c4faf9 | pdl/svd |
| https://github.com/Infineon/tc375-pac | d29acfe0975175cbad8930db0f85c2ef049e1477 | TC37XPD.svd |

## LICENSE & REDISTRIBUTION STATUS

Copies of every upstream license file are in `LICENSES/`. Statements below quote
text actually read from those files and from the SVD headers.

### mtb-pdl-cat1, mtb-pdl-cat2, mtb-dsl-pse8xxgp: Apache-2.0

Each repo LICENSE starts with "Apache License, Version 2.0, January 2004,
http://www.apache.org/licenses/". The SVD files themselves also carry an embedded
`licenseText` element stating "SPDX-License-Identifier: Apache-2.0" (checked in
psoc6_02.svd, psoc4100sp.svd, cat1c8m.svd, pse84.svd). Redistribution: fine with
attribution and the license text included, which this repo does.

### mtb-xmclib-cat3 (XMC1000, XMC4000): mixed per-file headers, restrictive repo EULA, review before publishing

The repo-level LICENSE is a Cypress EULA, not an open source license. It starts:
"CYPRESS (AN INFINEON COMPANY) END USER LICENSE AGREEMENT. PLEASE READ THIS END
USER LICENSE AGREEMENT ('Agreement') CAREFULLY BEFORE DOWNLOADING, INSTALLING,
COPYING, OR USING THIS SOFTWARE".

The individual SVD file headers do not all match the repo EULA, and they do not
all match each other:

- XMC4300, XMC4700, XMC4800 carry a BSD-3-Clause style header: "Redistribution
  and use in source and binary forms, with or without modification, are permitted
  provided that the following conditions are met" plus the usual three clauses.
- XMC1100, XMC1200, XMC1300, XMC1400, XMC4100, XMC4200, XMC4500 carry an Infineon
  notice instead: "This file can be freely distributed within development tools
  that are supporting such microcontrollers."
- XMC4400 has no license header at all (only tool and release-note comments).

Note: the working assumption was that all XMC SVDs carry BSD-style headers. Only
3 of 11 do. Treat the whole XMC set as: permissive or tools-only per-file terms,
restrictive repo EULA. Review before publishing outside a development tool context.

### tc375-pac (AURIX): restricted, development tools only

The repo LICENSE and the `licenseText` element inside TC37XPD.svd carry the same
Infineon notice: "Infineon Technologies AG (Infineon) is supplying this software
for use with Infineon's microcontrollers. This file can be freely distributed
within development tools that are supporting such microcontrollers." That is not
an open source license. Distribution is allowed within development tools only.
Do not republish standalone.

## Provenance legend

- pristine: byte-identical copy of the upstream file (all files in this repo)
- patched: locally modified (none)
- community: third-party origin (none)
- converted: generated from another format (none)

## Refresh

    python fetch.py

The fetch is incremental: it checks upstream versions first (git ls-remote per
repo against the SHAs in manifest.json) and downloads only the sources that
changed. A GitHub Action (`.github/workflows/check-updates.yml`) runs it weekly
(Monday 06:00 UTC) and commits any updates. If `manifest.json` or the family
folders are missing, the script does a full rebuild. Add `--clean` to delete `.work/`
afterwards. Needs git and Python 3 (stdlib only).

## Known gaps and issues

- fx3g2.svd (EZ-USB FX3G2, from mtb-pdl-cat1 COMPONENT_CAT1A) is malformed XML
  upstream (mismatched tag around line 60751, an unescaped `<` in a description
  swallows a closing tag). Dropped from the collection, recorded in manifest.json.
- AURIX coverage is TC375 only. Infineon publishes no other AURIX SVDs.
- Some TRAVEO parts named in older PDL releases (tviibe512k, tviibh4m, tviibh8m,
  tviice4m) are not present at the mtb-pdl-cat1 SHA above.
- XMC4400 has no per-file license header, see the license section.
