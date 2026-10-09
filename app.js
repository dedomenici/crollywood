/* Crollywood – self-guided Croydon movie location walk. Leaflet + OSM, no API keys. Monochrome. */
(function () {
  'use strict';
  var ARRIVE_M = 30;          // base arrival radius
  var ARRIVE_ACC_BONUS = 20;  // radius grows with GPS uncertainty, up to +20 m
  var MAX_ACC_FOR_ARRIVAL = 75; // ignore fixes worse than this for auto-arrive
  var STALE_MS = 30000;
  var PASSWORD = 'konga';     // client-side gate only (case-insensitive) – not real security
  var LS = { unlock: 'crollywood.unlocked', visited: 'crollywood.visited', tour: 'crollywood.tour' };

  var state = {
    stops: [], markers: [], current: 0, mode: 'home', routeBounds: null,
    visited: JSON.parse(localStorage.getItem(LS.visited) || '{}'),
    tour: JSON.parse(localStorage.getItem(LS.tour) || '{"active":false,"target":0,"finishing":false}'),
    geo: { watchId: null, me: null, acc: null, lastFix: 0, follow: false, marker: null, circle: null, restartTimer: null, gotFix: false },
    toasted: {}, log: [], wakeLock: null, lastArrived: -1
  };
  var $ = function (id) { return document.getElementById(id); };
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]; }); }
  function log(type, data) { state.log.push({ t: Date.now(), type: type, data: data }); }
  function saveTour() { localStorage.setItem(LS.tour, JSON.stringify(state.tour)); }

  /* ---------- password gate ---------- */
  if (localStorage.getItem(LS.unlock) !== '1') $('gate').hidden = false;
  $('gateForm').addEventListener('submit', function (e) {
    e.preventDefault();
    if ($('gatePw').value.trim().toLowerCase() === PASSWORD) {
      localStorage.setItem(LS.unlock, '1'); $('gate').hidden = true;
      setTimeout(function () { map.invalidateSize(); goHome(); }, 50);
    } else {
      $('gateMsg').textContent = 'Wrong password. Ask Richard!';
      var f = $('gateForm'); f.classList.remove('shake'); void f.offsetWidth; f.classList.add('shake');
    }
  });

  /* ---------- map ---------- */
  var map = L.map('map', { zoomControl: false, attributionControl: false }).setView([51.3745, -0.0990], 16);
  L.control.attribution({ position: 'topleft', prefix: false }).addTo(map);
  // Colour satellite imagery (Esri World Imagery – free to use with attribution, no key) + street/label overlays
  L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    maxZoom: 20, maxNativeZoom: 19,
    attribution: 'Imagery &amp; labels &copy; Esri, Maxar, Earthstar Geographics'
  }).addTo(map);
  L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/{z}/{y}/{x}', {
    maxZoom: 20, maxNativeZoom: 19, opacity: 0.55
  }).addTo(map);
  L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}', {
    maxZoom: 20, maxNativeZoom: 19, opacity: 0.9
  }).addTo(map);
  var ACCENT = '#14b8a6';

  function haversine(a, b) {
    var R = 6371000, toR = Math.PI / 180, dLat = (b[0] - a[0]) * toR, dLng = (b[1] - a[1]) * toR;
    var h = Math.sin(dLat / 2) * Math.sin(dLat / 2) + Math.cos(a[0] * toR) * Math.cos(b[0] * toR) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
    return 2 * R * Math.asin(Math.sqrt(h));
  }
  function bearing(a, b) {
    var toR = Math.PI / 180, y = Math.sin((b[1] - a[1]) * toR) * Math.cos(b[0] * toR);
    var x = Math.cos(a[0] * toR) * Math.sin(b[0] * toR) - Math.sin(a[0] * toR) * Math.cos(b[0] * toR) * Math.cos((b[1] - a[1]) * toR);
    return (Math.atan2(y, x) / toR + 360) % 360;
  }
  function compass(deg) { return ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'][Math.round(deg / 45) % 8]; }
  function fmtDist(m) { return m < 1000 ? Math.round(m) + ' m' : (m / 1000).toFixed(2) + ' km'; }
  function fmtWalk(m) { return Math.max(1, Math.round(m / 80)) + ' min'; }
  function ll(s) { return [s.lat, s.lng]; }
  // distance used for arrival: nearer of the pin and the point where the walking route passes it
  function arrivalDist(p, s) {
    var d = haversine(p, ll(s));
    if (s.route_snap) d = Math.min(d, haversine(p, [s.route_snap.lat, s.route_snap.lng]));
    return d;
  }

  /* ---------- clapperboard markers ---------- */
  function clapSVG(num, mode) {
    var board = mode === 'current' ? ACCENT : mode === 'visited' ? '#6a6a6a' : '#000';
    var text = mode === 'current' ? '#000' : '#fff', stroke = mode === 'current' ? '#000' : '#fff';
    var fs = String(num).length > 1 ? 13 : 15;
    return '<svg width="36" height="36" viewBox="0 0 36 36" xmlns="http://www.w3.org/2000/svg">' +
      '<g transform="rotate(-14 3 11)"><rect x="3" y="5" width="30" height="7" fill="#000" stroke="#fff" stroke-width="1.3"/>' +
      '<path d="M7 5 L11 12 M15 5 L19 12 M23 5 L27 12 M31 5 L33 8.5" stroke="#fff" stroke-width="2.6"/></g>' +
      '<rect x="3" y="12" width="30" height="5" fill="#000" stroke="#fff" stroke-width="1.3"/>' +
      '<path d="M7 12 L11 17 M15 12 L19 17 M23 12 L27 17" stroke="#fff" stroke-width="2.6"/>' +
      '<rect x="3" y="17" width="30" height="17" rx="1.5" fill="' + board + '" stroke="' + stroke + '" stroke-width="1.5"/>' +
      '<text x="18" y="30.5" text-anchor="middle" font-family="Anton,Impact,Arial Black,sans-serif" font-size="' + fs + '" fill="' + text + '">' + num + '</text></svg>';
  }
  function highlightIdx() { return state.mode === 'stop' ? state.current : (state.tour.active ? state.tour.target : -1); }
  function iconFor(i) {
    var s = state.stops[i], hi = highlightIdx();
    var mode = i === hi ? 'current' : state.visited[s.id] ? 'visited' : 'normal';
    return L.divIcon({ className: 'clap' + (mode === 'current' ? ' current' : ''), html: clapSVG(s.order, mode), iconSize: [36, 36], iconAnchor: [18, 34] });
  }
  function refreshIcons() { var hi = highlightIdx(); state.markers.forEach(function (m, i) { m.setIcon(iconFor(i)); m.setZIndexOffset(i === hi ? 500 : 0); }); }

  /* ---------- sheets / layout ---------- */
  function visibleSheet() { return state.mode === 'stop' ? $('panel') : $('home'); }
  function sheetHeight() { var s = visibleSheet(); return s && !s.hidden ? s.getBoundingClientRect().height : 0; }
  function layoutMapBtns() { $('mapBtns').style.bottom = (sheetHeight() + 12) + 'px'; }
  function fitRoute() {
    if (!state.routeBounds) return;
    map.fitBounds(state.routeBounds, { paddingTopLeft: [16, 34], paddingBottomRight: [16, sheetHeight() + 10] });
  }
  function panToVisible(p) {
    var pt = map.project(p, map.getZoom()).add([0, sheetHeight() / 2 - 16]);
    map.panTo(map.unproject(pt, map.getZoom()));
  }
  function goHome() {
    state.mode = 'home';
    $('panel').hidden = true; $('panel').style.transform = '';
    $('home').hidden = false;
    renderHome(); refreshIcons(); layoutMapBtns(); fitRoute(); updateStatus(); updateStreetView();
    log('home');
  }
  function renderHome() {
    var n = state.stops.length, v = state.stops.filter(function (s) { return state.visited[s.id]; }).length;
    $('progressBar').style.width = (n ? 100 * v / n : 0) + '%';
    $('progressText').textContent = v + ' / ' + n + ' visited';
    var t = state.tour;
    $('startBtn').textContent = t.active ? '▶ RESUME TOUR' : (n && v === n ? '↺ START AGAIN' : v > 0 ? '▶ CONTINUE TOUR' : '▶ START TOUR');
    $('endBtn').hidden = !t.active;
  }

  /* ---------- stop panel: carousel + media ---------- */
  function slides(s) {
    var out = [], photoSrc = s.image && (s.image.src || s.image.url);
    out.push(photoSrc
      ? '<figure class="slide"><span class="tag">Location</span><img src="' + esc(photoSrc) + '" alt="' + esc(s.name) + '" loading="lazy"' +
        (s.image.src && s.image.url ? ' data-fallback="' + esc(s.image.url) + '"' : '') + '><figcaption>' + esc(s.image.credit || '') + ' · ' + esc(s.image.license || '') + '</figcaption></figure>'
      : '<figure class="slide"><span class="tag">Location</span><img src="media/images/' + esc(s.id) + '.jpg" alt="" data-ph="📷 Location photo placeholder: add media/images/' + esc(s.id) + '.jpg"></figure>');
    s.films.forEach(function (f) {
      if (f.poster) out.push('<figure class="slide poster"><span class="tag">Poster</span><img src="' + esc(f.poster.src) + '" alt="' + esc(f.title) + ' poster" loading="lazy"><figcaption>' + esc(f.title) + ': ' + esc(f.poster.credit) + '</figcaption></figure>');
      else if (f.type !== 'venue' && f.type !== 'redux') out.push('<figure class="slide poster"><span class="tag">Poster</span><div class="placeholder">🎞 ' + esc(f.title) + '<br>poster not yet available<br>(add to media/posters/)</div></figure>');
    });
    return out;
  }
  function carouselHTML(s) {
    var sl = slides(s);
    var dots = sl.length > 1 ? '<div class="dots">' + sl.map(function (_, i) { return '<button data-i="' + i + '" class="' + (i ? '' : 'on') + '" aria-label="Slide ' + (i + 1) + '"></button>'; }).join('') + '</div>' : '';
    return '<div class="carousel"><div class="track" id="track">' + sl.join('') + '</div>' + dots + '</div>';
  }
  function wireCarousel() {
    var track = $('track'); if (!track) return;
    track.querySelectorAll('img').forEach(function (img) {
      img.addEventListener('error', function () {
        if (img.dataset.fallback && img.src.indexOf(img.dataset.fallback) < 0) { img.src = img.dataset.fallback; return; }
        img.outerHTML = '<div class="placeholder">' + esc(img.dataset.ph || 'Image unavailable') + '</div>';
      });
    });
    var dots = document.querySelectorAll('.dots button');
    dots.forEach(function (d) { d.onclick = function () { track.scrollTo({ left: (track.clientWidth + 8) * (+d.dataset.i), behavior: 'smooth' }); }; });
    track.addEventListener('scroll', function () {
      var i = Math.round(track.scrollLeft / (track.clientWidth + 8));
      dots.forEach(function (d, k) { d.classList.toggle('on', k === i); });
    }, { passive: true });
  }
  function mediaHTML(s) {
    return '<div class="media-label">Clip</div><div id="clipSlot"><video controls playsinline preload="metadata" src="' + esc(s.clip) + '"></video></div>' +
      '<div class="media-label">Narration</div><div id="audioSlot"><audio controls preload="metadata" src="' + esc(s.audio) + '"></audio></div>';
  }
  function wireMedia(s) {
    var v = document.querySelector('#clipSlot video'), a = document.querySelector('#audioSlot audio');
    if (v) v.addEventListener('error', function () { $('clipSlot').innerHTML = '<div class="placeholder">🎬 Video clip placeholder<br><code>' + esc(s.clip) + '</code></div>'; });
    if (a) a.addEventListener('error', function () { $('audioSlot').innerHTML = '<div class="placeholder" style="height:60px">🎧 Narration placeholder: <code>' + esc(s.audio) + '</code></div>'; });
  }
  function renderPanel(banner) {
    var s = state.stops[state.current];
    $('stopNum').textContent = s.order + '/' + state.stops.length;
    $('stopName').textContent = s.name;
    var h = banner ? '<div class="arrived-banner">' + esc(banner) + '</div>' : '';
    h += '<div class="addr">' + esc(s.address || '') + '</div><div class="dist" id="panelDist"></div>';
    h += carouselHTML(s);
    s.films.forEach(function (f) {
      h += '<div class="film"><h3>' + esc(f.title) + (f.year ? ' (' + esc(f.year) + ')' : '') + '</h3><div class="meta">' + esc(f.type || '') + '</div><p>' + esc(f.scene) + '</p></div>';
    });
    h += mediaHTML(s);
    if (s.leg_to_next_m) h += '<p class="small">To the next stop: ' + fmtDist(s.leg_to_next_m) + ' along the route.</p>';
    h += '<div class="btnrow"><button id="visitBtn">' + (state.visited[s.id] ? '✓ Visited' : 'Mark visited') + '</button><button id="dirBtn">Walk here (OSM)</button></div>';
    h += '<p><span class="conf ' + esc(s.confidence) + '">' + esc(s.confidence) + ' confidence</span> <span class="sources">' + esc(s.confidence_note || '') + '</span></p>';
    h += '<div class="sources">Sources: ' + s.sources.map(function (x) {
      return /^https?:/.test(x) ? '<a href="' + esc(x.split(' ')[0]) + '" target="_blank" rel="noopener">' + esc(x.split(' ')[0].replace(/^https?:\/\/(www\.)?/, '').slice(0, 48)) + '</a>' : esc(x);
    }).join(' · ') + '</div>';
    $('panelBody').innerHTML = h; $('panelBody').scrollTop = 0;
    wireCarousel(); wireMedia(s);
    $('visitBtn').onclick = function () { setVisited(s, !state.visited[s.id]); renderPanel(); };
    $('dirBtn').onclick = function () {
      var from = state.geo.me ? state.geo.me.join(',') : '';
      window.open('https://www.openstreetmap.org/directions?engine=fossgis_osrm_foot&route=' + encodeURIComponent(from) + '%3B' + s.lat + '%2C' + s.lng, '_blank');
    };
    updateStatus();
  }
  function setVisited(s, v) {
    if (v) state.visited[s.id] = Date.now(); else delete state.visited[s.id];
    localStorage.setItem(LS.visited, JSON.stringify(state.visited)); refreshIcons();
  }
  function goTo(i, opts) {
    opts = opts || {};
    var n = state.stops.length; state.current = ((i % n) + n) % n;
    state.mode = 'stop';
    $('home').hidden = true; $('panel').hidden = false; $('panel').style.transform = '';
    renderPanel(opts.banner); refreshIcons(); layoutMapBtns(); updateStreetView();
    if (!opts.noPan) panToVisible(ll(state.stops[state.current]));
  }

  /* ---------- Street View corner (keyless legacy embed + official link fallback) ---------- */
  function svPoint(s) { return s.route_snap ? [s.route_snap.lat, s.route_snap.lng] : ll(s); }
  function svHeading(s) { var a = svPoint(s); return haversine(a, ll(s)) > 3 ? Math.round(bearing(a, ll(s))) : 0; }
  function svEmbedUrl(s) { var a = svPoint(s); return 'https://maps.google.com/maps?layer=c&cbll=' + a[0] + ',' + a[1] + '&cbp=11,' + svHeading(s) + ',0,0,0&output=svembed'; }
  function svLinkUrl(s) { var a = svPoint(s); return 'https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=' + a[0] + ',' + a[1] + '&heading=' + svHeading(s); }
  var svOpen = localStorage.getItem('crollywood.sv') !== '0';
  function updateStreetView() {
    var box = $('sv'), s = state.stops[state.current];
    if (state.mode !== 'stop' || !s) { box.hidden = true; $('svFrame').src = 'about:blank'; return; }
    box.hidden = false;
    $('svOpenLink').href = svLinkUrl(s);
    box.classList.toggle('min', !svOpen);
    var want = svOpen ? svEmbedUrl(s) : 'about:blank';
    if ($('svFrame').getAttribute('src') !== want) $('svFrame').setAttribute('src', want);
  }
  $('svToggle').onclick = function () { svOpen = !svOpen; localStorage.setItem('crollywood.sv', svOpen ? '1' : '0'); updateStreetView(); };

  /* ---------- swipe down to close ---------- */
  (function () {
    var drag = $('panelDrag'), panel = $('panel'), y0 = null, dy = 0, t0 = 0, active = false;
    drag.addEventListener('pointerdown', function (e) { y0 = e.clientY; dy = 0; t0 = Date.now(); active = false; });
    window.addEventListener('pointermove', function (e) {
      if (y0 === null) return;
      dy = Math.max(0, e.clientY - y0);
      if (!active && dy > 8) { active = true; panel.classList.add('dragging'); }
      if (active) { panel.style.transform = 'translateY(' + dy + 'px)'; e.preventDefault(); }
    }, { passive: false });
    function end() {
      if (y0 === null) return;
      var v = dy / Math.max(1, Date.now() - t0);
      panel.classList.remove('dragging');
      if (active && (dy > 90 || v > 0.6)) goHome(); else panel.style.transform = '';
      y0 = null;
      if (active) { var swallow = function (ev) { ev.stopPropagation(); ev.preventDefault(); window.removeEventListener('click', swallow, true); }; window.addEventListener('click', swallow, true); setTimeout(function () { window.removeEventListener('click', swallow, true); }, 50); }
    }
    window.addEventListener('pointerup', end); window.addEventListener('pointercancel', end);
  })();

  /* ---------- status line ---------- */
  function setHomeMsg(msg, isErr) { var m = $('homeMsg'); m.textContent = msg || ''; m.classList.toggle('err', !!isErr); }
  function updateStatus() {
    var g = state.geo, n = state.stops.length;
    if (!n) return;
    if (g.watchId === null) $('gpsStatus').textContent = state.mode === 'home' ? n + ' stops · ' + (state.routeKm || '?') + ' km' : 'GPS off';
    else if (!g.me) $('gpsStatus').textContent = 'Locating…';
    else {
      var stale = Date.now() - g.lastFix > STALE_MS;
      $('gpsStatus').textContent = (stale ? 'GPS stale · ' : '') + '±' + Math.round(g.acc) + ' m';
      $('gpsStatus').classList.toggle('statusbar-warn', stale || g.acc > MAX_ACC_FOR_ARRIVAL);
    }
    var tgtIdx = state.tour.active ? state.tour.target : (state.mode === 'stop' ? state.current : -1);
    if (tgtIdx < 0) { $('nextInfo').textContent = state.tour.active ? '' : 'Tap ▶ START TOUR'; }
    else {
      var t = state.stops[tgtIdx];
      var label = (state.tour.active ? (state.tour.finishing ? 'Finish → ' : 'Next → ') : '') + t.order + '. ' + t.name;
      if (g.me) {
        var d = haversine(g.me, ll(t));
        label += ': ' + fmtDist(d) + ' ' + compass(bearing(g.me, ll(t)));
      }
      $('nextInfo').textContent = label;
    }
    var pd = $('panelDist');
    if (pd && state.mode === 'stop') {
      var s = state.stops[state.current];
      pd.textContent = g.me ? fmtDist(haversine(g.me, ll(s))) + ' away (as the crow flies, ' + compass(bearing(g.me, ll(s))) + ') · ~' + fmtWalk(haversine(g.me, ll(s))) + ' walk' : '';
    }
    $('locateBtn').classList.toggle('on', g.watchId !== null);
    $('locateBtn').textContent = g.watchId !== null ? '◉ GPS on' : '◉ GPS';
  }
  setInterval(updateStatus, 5000);

  /* ---------- geolocation ---------- */
  var GEO_OPTS = { enableHighAccuracy: true, maximumAge: 3000, timeout: 20000 };
  function startTracking() {
    var g = state.geo;
    if (!window.isSecureContext) { setHomeMsg('Live location needs HTTPS. Open the https:// version of this page.', true); log('geo-error', 'insecure'); return false; }
    if (!('geolocation' in navigator)) { setHomeMsg('This browser has no location support. Use ◀ ▶ to move between stops.', true); log('geo-error', 'unsupported'); return false; }
    if (g.watchId !== null) return true;
    g.gotFix = false;
    g.watchId = navigator.geolocation.watchPosition(onPosition, onPosError, GEO_OPTS);
    log('geo-start'); updateStatus();
    return true;
  }
  function stopTracking() {
    var g = state.geo;
    if (g.watchId !== null) navigator.geolocation.clearWatch(g.watchId);
    clearTimeout(g.restartTimer);
    g.watchId = null; setFollow(false);
    if (g.marker) { map.removeLayer(g.marker); map.removeLayer(g.circle); g.marker = g.circle = null; }
    g.me = null; log('geo-stop'); updateStatus();
  }
  function restartWatch() { // some browsers stop delivering after errors – re-arm the watch
    var g = state.geo; if (g.watchId === null) return;
    navigator.geolocation.clearWatch(g.watchId);
    g.watchId = navigator.geolocation.watchPosition(onPosition, onPosError, GEO_OPTS); log('geo-restart');
  }
  function onPosition(pos) {
    var g = state.geo, c = pos.coords, p = [c.latitude, c.longitude];
    var first = !g.gotFix;
    g.me = p; g.acc = c.accuracy; g.lastFix = Date.now(); g.gotFix = true;
    clearTimeout(g.restartTimer);
    if (!g.marker) {
      g.circle = L.circle(p, { radius: c.accuracy, color: '#ff2a2a', weight: 1, fillColor: '#ff2a2a', fillOpacity: 0.12, interactive: false }).addTo(map);
      g.marker = L.marker(p, { icon: L.divIcon({ className: 'me-wrap', html: '<span class="me-pulse"></span><span class="me-dot"></span>', iconSize: [18, 18], iconAnchor: [9, 9] }), zIndexOffset: 1000, interactive: false }).addTo(map);
    } else { g.marker.setLatLng(p); g.circle.setLatLng(p).setRadius(c.accuracy); }
    if (first) { setHomeMsg(''); if (state.tour.active) setFollow(true); }
    if (g.follow) panToVisible(p);
    log('fix', { lat: p[0], lng: p[1], acc: c.accuracy });
    checkArrival(p, c.accuracy);
    updateStatus();
  }
  function onPosError(err) {
    var g = state.geo, msg;
    log('geo-error', err.code);
    if (err.code === 1) { // PERMISSION_DENIED – watch is dead
      msg = 'Location permission denied. Allow location for this site in your browser settings (iPhone: Settings › Privacy › Location Services › Safari Websites). You can still use ◀ ▶ to move between stops.';
      stopTracking();
    } else if (err.code === 2) {
      msg = 'Location unavailable right now (indoors, or GPS off?). Still trying…';
      g.restartTimer = setTimeout(restartWatch, 5000);
    } else {
      msg = 'Still waiting for a GPS fix… Try stepping outside.';
      g.restartTimer = setTimeout(restartWatch, 2000);
    }
    var recent = g.lastFix && Date.now() - g.lastFix < STALE_MS;
    log('geo-error-detail', { code: err.code, msg: err.message, recentFix: !!recent });
    if (err.code === 1 || !recent) { setHomeMsg(msg, true); showToast(msg, 6000); }
    if (recent && err.code !== 1) { updateStatus(); return; } // transient blip while we still have a fresh position
    $('gpsStatus').textContent = err.code === 1 ? 'GPS denied' : err.code === 2 ? 'GPS unavailable' : 'GPS timeout';
  }
  function setFollow(on) {
    state.geo.follow = on; $('followBtn').setAttribute('aria-pressed', on ? 'true' : 'false');
    if (on && state.geo.me) panToVisible(state.geo.me);
  }
  map.on('dragstart', function () { if (state.geo.follow) setFollow(false); });

  /* ---------- tour + arrival ---------- */
  function nextUnvisitedAfter(i) {
    for (var j = i + 1; j < state.stops.length; j++) if (!state.visited[state.stops[j].id]) return j;
    return -1;
  }
  function firstTarget() {
    if (!state.visited[state.stops[0].id]) return 0;
    var j = nextUnvisitedAfter(0); return j < 0 ? 0 : j;
  }
  function advanceTarget(fromIdx) {
    var j = nextUnvisitedAfter(fromIdx);
    if (j < 0) { // also pick up any skipped earlier stops before heading home
      for (var k = 1; k < fromIdx; k++) if (!state.visited[state.stops[k].id]) { j = k; break; }
    }
    if (j < 0) { state.tour.target = 0; state.tour.finishing = true; }
    else { state.tour.target = j; state.tour.finishing = false; }
    saveTour();
  }
  function checkArrival(p, acc) {
    if (!state.tour.active || !$('autoArrive').checked) return;
    if (acc > MAX_ACC_FOR_ARRIVAL) return; // too fuzzy to trust
    var radius = ARRIVE_M + Math.min(acc, ARRIVE_ACC_BONUS);
    var ti = state.tour.target, t = state.stops[ti];
    var d = arrivalDist(p, t);
    // clustered stops: only count the target once you're nearer to it than to the stop you just arrived at
    var la = state.lastArrived, dLast = la >= 0 && la !== ti ? arrivalDist(p, state.stops[la]) : Infinity;
    if (d <= radius && d < dLast) { arrive(ti, d); return; }
    // near another unvisited stop that isn't the target → gentle nudge only
    var best = -1, bd = 1e9;
    state.stops.forEach(function (s, i) {
      if (i === ti || state.visited[s.id] || state.toasted[s.id]) return;
      var di = arrivalDist(p, s); if (di <= radius && di < bd) { bd = di; best = i; }
    });
    if (best >= 0) {
      var s = state.stops[best]; state.toasted[s.id] = 1;
      log('nearby', { id: s.id, d: Math.round(bd) });
      showToast('You\'re passing stop ' + s.order + ': ' + s.films[0].title + '. Tap to view.', 8000, function () { goTo(best, {}); });
    }
  }
  function arrive(i, d) {
    var s = state.stops[i];
    if (state.tour.finishing && i === 0) {
      setVisited(s, true);
      state.tour.active = false; state.tour.finishing = false; saveTour();
      log('arrive', { id: s.id, d: Math.round(d), complete: true });
      if (navigator.vibrate) navigator.vibrate([300, 100, 300, 100, 300]);
      goTo(0, { banner: '🎬 That\'s a wrap! Tour complete. Enjoy the David Lean Cinema.' });
      releaseWakeLock(); return;
    }
    setVisited(s, true); state.lastArrived = i;
    log('arrive', { id: s.id, d: Math.round(d) });
    if (navigator.vibrate) navigator.vibrate([200, 100, 200]);
    advanceTarget(i);
    var nx = state.stops[state.tour.target];
    goTo(i, { banner: 'You have arrived: stop ' + s.order + '. Next: ' + (state.tour.finishing ? 'back to the David Lean Cinema' : nx.order + '. ' + nx.name) });
  }
  function startTour() {
    if (!state.stops.length) return;
    var allDone = state.stops.every(function (s) { return state.visited[s.id]; });
    if (allDone && !state.tour.active) { state.visited = {}; state.toasted = {}; state.lastArrived = -1; localStorage.setItem(LS.visited, '{}'); }
    state.tour.active = true; state.tour.finishing = false; state.tour.target = firstTarget();
    if (state.visited[state.stops[0].id] && state.tour.target === 0) state.tour.finishing = true;
    saveTour(); log('tour-start', state.tour.target);
    var ok = startTracking();
    if (ok) { setFollow(true); setHomeMsg('Getting your location…'); }
    requestWakeLock();
    goTo(state.tour.target, { banner: state.tour.target === 0 ? 'Tour started. Head to stop 1, the David Lean Cinema.' : 'Tour resumed. Head to stop ' + state.stops[state.tour.target].order + '.' });
    if (state.geo.me) checkArrival(state.geo.me, state.geo.acc);
  }
  function endTour() {
    state.tour.active = false; state.tour.finishing = false; saveTour();
    stopTracking(); releaseWakeLock(); log('tour-end'); setHomeMsg('Tour ended. Your progress is saved.'); goHome();
  }
  function resetProgress() {
    if (!confirm('Reset all visited stops and end the tour?')) return;
    state.visited = {}; localStorage.setItem(LS.visited, '{}'); state.toasted = {};
    state.tour = { active: false, target: 0, finishing: false }; saveTour();
    stopTracking(); releaseWakeLock(); setHomeMsg('Progress reset.'); goHome();
  }

  /* ---------- screen wake lock (keeps GPS alive while walking) ---------- */
  function requestWakeLock() {
    if (!('wakeLock' in navigator)) return;
    navigator.wakeLock.request('screen').then(function (l) { state.wakeLock = l; }).catch(function () {});
  }
  function releaseWakeLock() { if (state.wakeLock) { state.wakeLock.release().catch(function () {}); state.wakeLock = null; } }
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'visible' && state.tour.active) { requestWakeLock(); if (state.geo.watchId === null) startTracking(); }
  });

  /* ---------- toast ---------- */
  var toastTimer = null;
  function showToast(msg, ms, onTap) {
    var t = $('toast'); t.textContent = msg; t.hidden = false;
    t.onclick = function () { t.hidden = true; if (onTap) onTap(); };
    clearTimeout(toastTimer); toastTimer = setTimeout(function () { t.hidden = true; }, ms || 4000);
  }

  /* ---------- credits ---------- */
  function buildCredits() {
    var ph = [], po = [], seen = {};
    state.stops.forEach(function (s) {
      if (s.image && s.image.credit) ph.push('<li>' + s.order + '. ' + esc(s.name) + ': ' + esc(s.image.credit) + ', ' + esc(s.image.license) +
        (s.image.page ? ' (<a href="' + esc(s.image.page) + '" target="_blank" rel="noopener">source</a>)' : '') + '</li>');
      s.films.forEach(function (f) { if (f.poster && !seen[f.poster.src]) { seen[f.poster.src] = 1; po.push('<li>' + esc(f.title) + ': <a href="' + esc(f.poster.page) + '" target="_blank" rel="noopener">Wikipedia</a></li>'); } });
    });
    $('photoCredits').innerHTML = ph.join(''); $('posterCredits').innerHTML = po.join('');
  }

  /* ---------- wiring ---------- */
  $('homeBtn').onclick = goHome;
  $('closeBtn').onclick = goHome;
  $('startBtn').onclick = startTour;
  $('endBtn').onclick = endTour;
  $('resetBtn').onclick = resetProgress;
  $('browseBtn').onclick = function () { goTo(state.tour.active ? state.tour.target : 0, {}); };
  $('prevBtn').onclick = function () { goTo(state.current - 1); };
  $('nextBtn').onclick = function () { goTo(state.current + 1); };
  $('locateBtn').onclick = function () { if (state.geo.watchId !== null) stopTracking(); else { startTracking(); setFollow(true); } };
  $('followBtn').onclick = function () {
    if (state.geo.watchId === null) { if (startTracking()) setFollow(true); return; }
    setFollow(!state.geo.follow);
  };
  $('fitBtn').onclick = function () { setFollow(false); fitRoute(); };
  $('creditsBtn').onclick = function () { $('credits').hidden = false; };
  $('creditsClose').onclick = function () { $('credits').hidden = true; };
  $('lockBtn').onclick = function () { localStorage.removeItem(LS.unlock); location.reload(); };
  window.addEventListener('resize', function () { layoutMapBtns(); });

  function init(data, route) {
    state.stops = data.stops.slice().sort(function (a, b) { return a.order - b.order; });
    state.routeKm = data.route_distance_m ? (data.route_distance_m / 1000).toFixed(1) : null;
    var line = route && route.features && route.features[0]
      ? route.features[0].geometry.coordinates.map(function (c) { return [c[1], c[0]]; })
      : state.stops.map(ll).concat([ll(state.stops[0])]);
    L.polyline(line, { color: '#000', weight: 8, opacity: 0.85, interactive: false }).addTo(map);
    var rl = L.polyline(line, { color: ACCENT, weight: 4, dashArray: '10 7', interactive: false }).addTo(map);
    state.routeBounds = rl.getBounds();
    state.stops.forEach(function (s, i) {
      var m = L.marker(ll(s), { icon: iconFor(i), title: s.order + '. ' + s.name }).addTo(map);
      m.on('click', function () { setFollow(false); goTo(i); });
      state.markers.push(m);
    });
    if (state.tour.target >= state.stops.length) state.tour.target = 0;
    buildCredits();
    goHome();
    if (state.tour.active) setHomeMsg('Tour in progress. Tap RESUME TOUR to turn location back on.');
  }
  Promise.all([
    fetch('locations.json').then(function (r) { return r.json(); }),
    fetch('route.geojson').then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; })
  ]).then(function (res) { init(res[0], res[1]); })
    .catch(function (e) { setHomeMsg('Could not load locations.json: ' + e.message, true); console.error(e); });

  window.crollywood = state; // debugging / test hook
})();
