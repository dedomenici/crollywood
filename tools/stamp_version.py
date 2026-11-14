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
def listfiles(d, exts=None):
    path = os.path.join("media", d)
    if not os.path.isdir(path):
        return []
    out = []
    for f in os.listdir(path):
        if f.startswith("."):
            continue
        fp = os.path.join(path, f)
        if not os.path.isfile(fp):
            continue
        if exts and not f.lower().endswith(exts):
            continue
        out.append(f)
    return sorted(out)
man = {
    "clips": listfiles("clips", (".mp4",)),
    "audio": listfiles("audio"),
    "clip_posters": listfiles("clips/posters", (".jpg", ".jpeg", ".webp", ".png")),
}
open("media/manifest.json", "w").write(json.dumps(man) + "\n")
print("build", v, "| media:", {k: len(x) for k, x in man.items()})
