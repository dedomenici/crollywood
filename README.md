# CROLLYWOOD

A self-guided walking tour of film and TV locations in Croydon town centre, by **Richard DeDomenici** ([dedomenici.com](https://dedomenici.com)) for [The Redux Project](https://thereduxproject.com) and [Croydonites Festival](https://www.croydonites.com).

The app is a static single page built with Leaflet and OpenStreetMap, with no API keys. The loop starts and ends at the David Lean Cinema (Croydon Clocktower).

- `locations.json`: stops, with films, scenes, sources and confidence ratings. This file is generated.
- `route.geojson`: the street-accurate walking loop, pre-computed with OSRM foot routing. This file is generated.
- `tools/stops_source.json`: the hand-edited stop data. To regenerate the two files above, run `python3 tools/build.py`. Add `--no-reorder` to keep the order you set.
- `media/clips/<id>.mp4`, `media/audio/<id>.mp3`, `media/images/<id>.jpg`: put your own media here. A missing file shows a placeholder.
- `media/photos/`: location photos (Wikimedia Commons, CC licensed). `media/posters/`: posters from Wikipedia, used to identify each film.

The password screen is client-side only. It's a soft gate and does not secure anything.
