/* Crollywood – self-guided Croydon movie location walk. Leaflet + OSM, no API keys. Monochrome. */
(function () {
  'use strict';
  var ARRIVE_M = 30;
  var PASSWORD = 'konga';               // client-side gate only (case-insensitive) – not real security
  var LS_UNLOCK = 'crollywood.unlocked', LS_VISITED = 'crollywood.visited';
  var state = { stops: [], markers: [], current: 0, me: null, meMarker: null, meCircle: null, watchId: null,
    visited: JSON.parse(localStorage.getItem(LS_VISITED) || '{}'), arrivedShown: {}, routeLine: null };
  var $ = function (id) { return document.getElementById(id); };
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]; }); }

  /* ---------- password gate ---------- */
  function unlocked() { return localStorage.getItem(LS_UNLOCK) === '1'; }
  if (!unlocked()) $('gate').hidden = false;
  $('gateForm').addEventListener('submit', function (e) {
    e.preventDefault();
    if ($('gatePw').value.trim().toLowerCase() === PASSWORD) {
      localStorage.setItem(LS_UNLOCK, '1'); $('gate').hidden = true; setTimeout(function () { map.invalidateSize(); }, 50);
    } else {
      $('gateMsg').textContent = 'Wrong password. Ask Richard!';
      var f = $('gateForm'); f.classList.remove('shake'); void f.offsetWidth; f.classList.add('shake');
    }
  });

  /* ---------- map ---------- */
  var map = L.map('map', { zoomControl: false }).setView([51.3745, -0.0990], 16);
  L.control.zoom({ position: 'bottomright' }).addTo(map);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(map);

  function haversine(a, b) {
    var R = 6371000, toR = Math.PI / 180, dLat = (b[0] - a[0]) * toR, dLng = (b[1] - a[1]) * toR;
    var h = Math.sin(dLat / 2) * Math.sin(dLat / 2) + Math.cos(a[0] * toR) * Math.cos(b[0] * toR) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
    return 2 * R * Math.asin(Math.sqrt(h));
  }
  function fmtDist(m) { return m < 1000 ? Math.round(m) + ' m' : (m / 1000).toFixed(2) + ' km'; }
  function fmtWalk(m) { return Math.max(1, Math.round(m / 80)) + ' min walk'; }

  /* ---------- clapperboard markers ---------- */
  function clapSVG(num, mode) {
    var board = mode === 'current' ? '#fff' : mode === 'visited' ? '#6a6a6a' : '#000';
    var text = mode === 'current' ? '#000' : '#fff';
    var stroke = mode === 'current' ? '#000' : '#fff';
    var fs = String(num).length > 1 ? 13 : 15;
    return '<svg width="36" height="36" viewBox="0 0 36 36" xmlns="http://www.w3.org/2000/svg">' +
      // hinged clapper (striped), slightly open
      '<g transform="rotate(-14 3 11)"><rect x="3" y="5" width="30" height="7" fill="#000" stroke="#fff" stroke-width="1.3"/>' +
      '<path d="M7 5 L11 12 M15 5 L19 12 M23 5 L27 12 M31 5 L33 8.5" stroke="#fff" stroke-width="2.6"/></g>' +
      // lower stick + board
      '<rect x="3" y="12" width="30" height="5" fill="#000" stroke="#fff" stroke-width="1.3"/>' +
      '<path d="M7 12 L11 17 M15 12 L19 17 M23 12 L27 17" stroke="#fff" stroke-width="2.6"/>' +
      '<rect x="3" y="17" width="30" height="17" rx="1.5" fill="' + board + '" stroke="' + stroke + '" stroke-width="1.5"/>' +
      '<text x="18" y="30.5" text-anchor="middle" font-family="Anton,Impact,Arial Black,sans-serif" font-size="' + fs + '" fill="' + text + '">' + num + '</text></svg>';
  }
  function iconFor(i) {
    var s = state.stops[i];
    var mode = i === state.current ? 'current' : state.visited[s.id] ? 'visited' : 'normal';
    return L.divIcon({ className: 'clap' + (mode === 'current' ? ' current' : ''), html: clapSVG(s.order, mode), iconSize: [36, 36], iconAnchor: [18, 34] });
  }
  function refreshIcons() { state.markers.forEach(function (m, i) { m.setIcon(iconFor(i)); m.setZIndexOffset(i === state.current ? 500 : 0); }); }

  /* ---------- panel: carousel + media ---------- */
  function slides(s) {
    var out = [];
    var photoSrc = s.image && (s.image.src || s.image.url);
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
    dots.forEach(function (d) { d.onclick = function () { track.scrollTo({ left: track.clientWidth * (+d.dataset.i) + 8 * (+d.dataset.i), behavior: 'smooth' }); }; });
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

  function renderPanel(arrived) {
    var s = state.stops[state.current];
    $('stopNum').textContent = s.order + '/' + state.stops.length;
    $('stopName').textContent = s.name;
    var h = '';
    if (arrived) h += '<div class="arrived-banner">You have arrived: stop ' + s.order + '</div>';
    h += '<div class="addr">' + esc(s.address || '') + '</div><div class="dist" id="panelDist"></div>';
    h += carouselHTML(s);
    s.films.forEach(function (f) {
      h += '<div class="film"><h3>' + esc(f.title) + (f.year ? ' (' + esc(f.year) + ')' : '') + '</h3>' +
        '<div class="meta">' + esc(f.type || '') + '</div><p>' + esc(f.scene) + '</p></div>';
    });
    h += mediaHTML(s);
    if (s.leg_to_next_m) h += '<p class="small">Next stop: ' + fmtDist(s.leg_to_next_m) + ' along the route.</p>';
    h += '<div class="btnrow"><button id="visitBtn">' + (state.visited[s.id] ? '✓ Visited' : 'Mark visited') + '</button><button id="dirBtn">Walk here (OSM)</button></div>';
    h += '<p><span class="conf ' + esc(s.confidence) + '">' + esc(s.confidence) + ' confidence</span> <span class="sources">' + esc(s.confidence_note || '') + '</span></p>';
    h += '<div class="sources">Sources: ' + s.sources.map(function (x) {
      return /^https?:/.test(x) ? '<a href="' + esc(x.split(' ')[0]) + '" target="_blank" rel="noopener">' + esc(x.split(' ')[0].replace(/^https?:\/\/(www\.)?/, '').slice(0, 48)) + '</a>' : esc(x);
    }).join(' · ') + '</div>';
    $('panelBody').innerHTML = h;
    $('panelBody').scrollTop = 0;
    wireCarousel(); wireMedia(s);
    $('visitBtn').onclick = function () { setVisited(s, !state.visited[s.id]); renderPanel(); };
    $('dirBtn').onclick = function () {
      var from = state.me ? state.me.join(',') : '';
      window.open('https://www.openstreetmap.org/directions?engine=fossgis_osrm_foot&route=' + encodeURIComponent(from) + '%3B' + s.lat + '%2C' + s.lng, '_blank');
    };
    updateNextInfo();
  }
  function setVisited(s, v) {
    if (v) state.visited[s.id] = Date.now(); else delete state.visited[s.id];
    localStorage.setItem(LS_VISITED, JSON.stringify(state.visited)); refreshIcons();
  }
  function panToVisible(ll) {
    var panelH = $('panel').classList.contains('collapsed') ? 64 : window.innerHeight * 0.72;
    var pt = map.project(ll, map.getZoom()).add([0, panelH / 2 - 30]);
    map.panTo(map.unproject(pt, map.getZoom()));
  }
  function goTo(i, opts) {
    opts = opts || {};
    var n = state.stops.length; state.current = ((i % n) + n) % n;
    refreshIcons(); renderPanel(opts.arrived);
    var s = state.stops[state.current];
    if (opts.expand) $('panel').classList.remove('collapsed');
    if (!opts.noPan) panToVisible([s.lat, s.lng]);
  }
  function updateNextInfo() {
    var s = state.stops[state.current];
    if (!state.me) { $('nextInfo').textContent = 'Stop ' + s.order + ': ' + s.films[0].title; $('panelDist').textContent = ''; return; }
    var d = haversine(state.me, [s.lat, s.lng]);
    $('nextInfo').textContent = '→ ' + s.order + '. ' + s.name + ': ' + fmtDist(d);
    var pd = $('panelDist'); if (pd) pd.textContent = fmtDist(d) + ' away (straight line) · ' + fmtWalk(d);
  }

  /* ---------- geolocation ---------- */
  function onPosition(pos) {
    var ll = [pos.coords.latitude, pos.coords.longitude], first = !state.me;
    state.me = ll;
    $('gpsStatus').textContent = '±' + Math.round(pos.coords.accuracy) + ' m';
    if (!state.meMarker) {
      state.meMarker = L.marker(ll, { icon: L.divIcon({ className: 'me-dot', iconSize: [18, 18] }), zIndexOffset: 1000 }).addTo(map);
      state.meCircle = L.circle(ll, { radius: pos.coords.accuracy, color: '#fff', weight: 1, fillOpacity: 0.08 }).addTo(map);
    } else { state.meMarker.setLatLng(ll); state.meCircle.setLatLng(ll).setRadius(pos.coords.accuracy); }
    if (first) map.panTo(ll);
    updateNextInfo();
    if ($('autoArrive').checked) {
      var s = state.stops[state.current];
      var hit = haversine(ll, [s.lat, s.lng]) <= ARRIVE_M ? state.current : -1;
      if (hit < 0) state.stops.forEach(function (t, i) { if (hit < 0 && !state.visited[t.id] && haversine(ll, [t.lat, t.lng]) <= ARRIVE_M) hit = i; });
      if (hit >= 0 && !state.arrivedShown[state.stops[hit].id]) {
        var t = state.stops[hit]; state.arrivedShown[t.id] = true; setVisited(t, true);
        if (navigator.vibrate) navigator.vibrate([200, 100, 200]);
        goTo(hit, { arrived: true, expand: true });
      }
    }
  }
  function onPosError(err) { $('gpsStatus').textContent = 'GPS: ' + err.message; }
  function toggleTracking() {
    if (!('geolocation' in navigator)) { $('gpsStatus').textContent = 'No geolocation'; return; }
    if (state.watchId !== null) {
      navigator.geolocation.clearWatch(state.watchId); state.watchId = null;
      $('locateBtn').classList.remove('on'); $('locateBtn').textContent = '◉ Track'; $('gpsStatus').textContent = 'Location off'; return;
    }
    $('gpsStatus').textContent = 'Locating…';
    state.watchId = navigator.geolocation.watchPosition(onPosition, onPosError, { enableHighAccuracy: true, maximumAge: 5000, timeout: 20000 });
    $('locateBtn').classList.add('on'); $('locateBtn').textContent = '◉ Tracking';
  }

  /* ---------- credits ---------- */
  function buildCredits() {
    var ph = [], po = [], seen = {};
    state.stops.forEach(function (s) {
      if (s.image && s.image.credit) ph.push('<li>' + s.order + '. ' + esc(s.name) + ': ' + esc(s.image.credit) + ', ' + esc(s.image.license) +
        (s.image.page ? ' (<a href="' + esc(s.image.page) + '" target="_blank" rel="noopener">source</a>)' : '') + '</li>');
      s.films.forEach(function (f) {
        if (f.poster && !seen[f.poster.src]) { seen[f.poster.src] = 1; po.push('<li>' + esc(f.title) + ': <a href="' + esc(f.poster.page) + '" target="_blank" rel="noopener">Wikipedia</a></li>'); }
      });
    });
    $('photoCredits').innerHTML = ph.join(''); $('posterCredits').innerHTML = po.join('');
  }
  $('creditsBtn').onclick = function () { $('credits').hidden = false; };
  $('creditsClose').onclick = function () { $('credits').hidden = true; };
  $('lockBtn').onclick = function () { localStorage.removeItem(LS_UNLOCK); location.reload(); };

  /* ---------- init ---------- */
  function init(data, route) {
    state.stops = data.stops.slice().sort(function (a, b) { return a.order - b.order; });
    var line;
    if (route && route.features && route.features[0]) {
      line = route.features[0].geometry.coordinates.map(function (c) { return [c[1], c[0]]; });
    } else { // fallback: straight segments
      line = state.stops.map(function (s) { return [s.lat, s.lng]; }); line.push(line[0]);
    }
    L.polyline(line, { color: '#000', weight: 8, opacity: 0.85 }).addTo(map);
    state.routeLine = L.polyline(line, { color: '#fff', weight: 4, dashArray: '10 7' }).addTo(map);
    state.stops.forEach(function (s, i) {
      var m = L.marker([s.lat, s.lng], { icon: iconFor(i), title: s.order + '. ' + s.name }).addTo(map);
      m.on('click', function () { goTo(i, { expand: true }); });
      state.markers.push(m);
    });
    map.fitBounds(state.routeLine.getBounds(), { padding: [20, 20] });
    var km = data.route_distance_m ? (data.route_distance_m / 1000).toFixed(1) : '?';
    $('gpsStatus').textContent = state.stops.length + ' stops · ' + km + ' km loop';
    buildCredits();
    goTo(0, { noPan: true });
  }
  $('prevBtn').onclick = function () { goTo(state.current - 1, { expand: true }); };
  $('nextBtn').onclick = function () { goTo(state.current + 1, { expand: true }); };
  $('stopHeading').onclick = $('panelHandle').onclick = function () { $('panel').classList.toggle('collapsed'); };
  $('locateBtn').onclick = toggleTracking;

  Promise.all([
    fetch('locations.json').then(function (r) { return r.json(); }),
    fetch('route.geojson').then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; })
  ]).then(function (res) { init(res[0], res[1]); })
    .catch(function (e) { $('panelBody').innerHTML = '<p>Could not load locations.json: ' + esc(e.message) + '</p>'; console.error(e); });

  window.crollywood = state;
})();
