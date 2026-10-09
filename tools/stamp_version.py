#!/usr/bin/env python3
"""Stamp a build id into index.html + app.js so browsers never mix cached old/new assets.
Run before every commit:  python3 tools/stamp_version.py"""
import re, time
v = time.strftime("%Y%m%d%H%M%S")
h = open("index.html").read()
h = re.sub(r'(href="style\.css)(\?v=[^"]*)?"', r'\1?v=%s"' % v, h)
h = re.sub(r'(src="app\.js)(\?v=[^"]*)?"', r'\1?v=%s"' % v, h)
h = re.sub(r"window\.CROLLY_BUILD='[^']*'", "window.CROLLY_BUILD='%s'" % v, h)
if "window.CROLLY_BUILD" not in h:
    h = h.replace('<script src="app.js', "<script>window.CROLLY_BUILD='%s';</script>\n<script src=\"app.js" % v, 1)
open("index.html", "w").write(h)
j = open("app.js").read()
j = re.sub(r"var BUILD = '[^']*';", "var BUILD = '%s';" % v, j)
open("app.js", "w").write(j)
print("build", v)
