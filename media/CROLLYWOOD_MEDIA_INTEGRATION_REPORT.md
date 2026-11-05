# Crollywood media integration report
Date: 2026-11-05 (Europe/London)
Repo: /workspace/crollywood (uncommitted; **no push**)

## Deduped image inventory (13 unique after hash dedupe; 1 near-visual-dupe skipped)

| Size | SHA256 (16) | Source ULID (canonical) | Content | Stop | Role | Dest path | image.src? |
|------|-------------|-------------------------|---------|------|------|-----------|------------|
| 63440 | cb9e87551281092b | 01M6P7TKDJW5W5NMBHG1QK5GCV.jpg | Wimpy + FADS period set, SGW | american-assassin | location / set | media/photos/american-assassin-wimpy.jpg | no (extra) |
| 1018316 | 47c95dfde332085a | 01M6P7TRHGYSZK3F169ZHTQTGH.jpg | Redfields + Pizza Hut + crane | american-assassin | location / Bandersnatch set | media/photos/american-assassin-redfields.jpg | no (extra) |
| 112294 | 3103caa090a9f63f | 01M6P7R72GHB17WQQT31Y5B1R2.jpg | Fairfield Halls empty concert hall | fairfield-halls | location photo | media/photos/fairfield-halls.jpg | **YES** |
| 189398 | 050cc79f922f0479 | 01M6P7R9G4MVG83VQJQQFVZDYP.jpg | Da Vinci Code: Tom Hanks / Langdon podium | fairfield-halls | film still | media/photos/fairfield-halls-film.jpg | no (app single-image; kept for later) |
| 6876792 | 431ed5c9f209aa46 | 01M6P7RBK9ZSTN4R9YWN60EFPX.png | The Bill then/now alley composite | the-bill | location ID composite | media/photos/the-bill.jpg (+ .png archive) | **YES** (was null) |
| 65162 | 651c4756d2bcb35e | 01M6P7RT6JYRCE62J75529828Y.jpg | Chelsea Girl + Mr Doodle shutter (Whitgift) | terry-and-june | modern Whitgift street | media/photos/terry-and-june-chelsea-girl.jpg | no (kept 1976 primary) |
| 20608 | d7d25e2ef0cb4c3e | 01M6P7SCBZR5FZ4X9EEMT7DXAQ.jpg | JLB Credit peep-show still (lo-res) | peep-show-canterbury | film still alt | media/photos/peep-show-canterbury-still.jpg | no |
| 166700 | 5a90b0e6703fca40 | 01M6P7SE8E036FH39EW7RSB7HZ.jpg | Fairfield audience / Da Vinci lecture wide | fairfield-halls | film still / lecture | media/photos/fairfield-halls-lecture.jpg | no (extra) |
| 47455 | 4456a7946b1edecf | 01M6P7SGW2FZC17R9DKNQ9SS6J.jpg | SOLEIL shopfront (Bandersnatch set) | american-assassin | location / set | media/photos/american-assassin-soleil.jpg | no (extra) |
| 71667 | d892803bd8e0f50c | 01M6P7SJMZFSJ7GYJW8BXDSX2K.jpg | Same lecture-hall audience (near-dupe of SE8E) | fairfield-halls | skipped near-dupe | *(not copied)* | — |
| 1361799 | ca2b23e793edbe0f | 01M6P7SNFXHHQMAPHD3PBPG3ER.jpg | Vintage WHSmith on St George's Walk pillar | american-assassin | location photo (best) | media/photos/american-assassin.jpg | **YES** |
| 107966 | 60ac6d2310e9410a | 01M6P7SX5F8QN25YSES3EZMGB3.jpg | JLB Credit exterior (better still) | peep-show-canterbury | film still (location-defining) | media/photos/peep-show-canterbury.jpg | **YES** |
| 155783 | 593909b828b89ad6 | 01M6P7SZNKYWECYK1CPT2W7TK0.jpg | Ford Capri UMF 179M + Mini Cab 01 946 | american-assassin | Bandersnatch period street | media/photos/american-assassin-capri.jpg | no (extra) |

Duplicates by hash (resent set): 11 image dups dropped; see inventory script. Unique image count after hash = 13; unique useful = 12 copied (+1 near-dupe skipped).

## locations.json image.src updates
- `the-bill`: null → `media/photos/the-bill.jpg`
- `american-assassin`: replaced Commons SGW with WHSmith Bandersnatch set photo
- `fairfield-halls`: replaced exterior with Concert Hall interior
- `peep-show-canterbury`: replaced Commons Canterbury House with JLB Credit film still

Film stills kept on disk but not in `image.src` (app supports one photo): fairfield-halls-film.jpg, fairfield-halls-lecture.jpg, peep-show-canterbury-still.jpg, plus SGW extras under american-assassin-*.jpg.

## Clips (7 of 7 expected now on disk)

| Source | Dest | Stop | Status |
|--------|------|------|--------|
| 01M6P7VBA7KZ73J0F67D4Y1D5T.mp4 | media/clips/konga.mp4 | konga | WIRED (KONGA title) |
| 01M6P7X5FCGTJPQGBHWW468NXZ.mov | media/clips/velvet-goldmine.mp4 | velvet-goldmine | WIRED (NEW YORK 1984) |
| 01M6P7YATF7Q1VQ5XE681N25BE.mp4 | media/clips/made-in-dagenham.mp4 | made-in-dagenham | WIRED (parent watchVideo) |
| 01M6P808EG2E54JATS1CXPKJ3E.mov | media/clips/man-who-knew-too-little.mp4 | man-who-knew-too-little | WIRED (parent watchVideo) |
| 01M6P7VEPVVPWCC7KC1Y3QRJTA.mov | media/clips/clip-pending-1.mp4 | ? | PENDING — Waltham General Hospital / lobby action |
| 01M6P7VQRPTC2NFP0E1VGCC8RR.mp4 | media/clips/clip-pending-2.mp4 | ? | PENDING — East Croydon / 1970s figures |
| 01M6P7VXSA5GGZ2BG4DD5GWQJN.mp4 | media/clips/clip-pending-3.mp4 | ? | PENDING — Mercedes KW14 VMA / bald man |

`locations.json` already had `clip: media/clips/<id>.mp4` for all stops; only files were missing. Pending clips are **not** pointed at by any stop (safe). See `media/CLIPS_PENDING_NOTES.txt`.

## Build / manifest
Ran `python3 tools/stamp_version.py` → refreshed `media/manifest.json` + build id in index.html/app.js.

## Ambiguities / follow-ups
1. Redfields+Pizza Hut could also argue for heads-of-state-sgw historically, but dressing is Bandersnatch 80s → kept under american-assassin extras.
2. Chelsea Girl+Mr Doodle is modern Whitgift (not period Bandersnatch shopfront) → terry-and-june extra, did not replace 1976 primary.
3. Three clips still need human ID before renaming off `clip-pending-*`.
4. App has no gallery: extras sit on disk for a future multi-image UI.
5. No git commit / push performed.

## Not posters
None of the uploads were clear theatrical posters; `media/posters/` untouched.
