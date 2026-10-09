#!/usr/bin/env python3
"""Stamp a build id into index.html + app.js so browsers never mix cached old/new assets.
Run before every commit:  python3 tools/stamp_version.py"""
import re, time
v = time.strftime("%Y%m%d%H%M%S")
h = open("index.html").read()
h = re.sub(r'(href="style\.css)(\?v=[^"]*)?"', r'\1?v=%s"' % v, h)
h = re.sub(r'(src="config\.js)(\?v=[^"]*)?"', r'\1?v=%s"' % v, h)
h = re.sub(r'(src="app\.js)(\?v=[^"]*)?"', r'\1?v=%s"' % v, h)
h = re.sub(r"window\.CROLLY_BUILD='[^']*'", "window.CROLLY_BUILD='%s'" % v, h)
if "window.CROLLY_BUILD" not in h:
    h = h.replace('<script src="app.js', "<script>window.CROLLY_BUILD='%s';</script>\n<script src=\"app.js" % v, 1)
open("index.html", "w").write(h)
j = open("app.js").read()
j = re.sub(r"var BUILD = '[^']*';", "var BUILD = '%s';" % v, j)
open("app.js", "w").write(j)
# media manifest: the app only requests clips/narration that actually exist (no 404s for placeholders)
import os, json
man = {d: sorted(f for f in os.listdir("media/" + d) if not f.startswith(".")) if os.path.isdir("media/" + d) else [] for d in ("clips", "audio")}
open("media/manifest.json", "w").write(json.dumps(man) + "\n")
print("build", v, "| media:", {k: len(x) for k, x in man.items()})
