// --- Map Spots logic (moved from map_spots.html) ---
window.loadAllMapSpots = function() {
  loadMapSpotsLocations('aida');
  loadMapSpotsLocations('atlans');
  loadMapSpotsLocations('lacleon');
  loadMapSpotsLocations('icarus2');
}

async function loadMapSpotsLocations(map) {
  const endpoints = {
    aida: '/api/locations/aida',
    atlans: '/api/locations/atlans',
    lacleon: '/api/locations/lacleon',
    icarus2: '/api/locations/icarus2',
  };
  const selectId = `map-spots-${map}`;
  try {
    const response = await fetch(endpoints[map]);
    if (!response.ok) throw new Error(`Failed to load ${map} locations`);
    const locations = await response.json();
    const select = document.getElementById(selectId);
    if (!select) return;
    select.innerHTML = '<option value="">-- Wybierz spot --</option>';
    locations.forEach(location => {
      const opt = document.createElement('option');
      opt.value = location.id;
      opt.textContent = `${location.id} (${location.moobs})`;
      opt.dataset.location = JSON.stringify(location);
      select.appendChild(opt);
    });
  } catch (error) {
    const select = document.getElementById(selectId);
    if (select) select.innerHTML = `<option value="">Błąd: ${error.message}</option>`;
  }
}

async function saveMapSpots(map) {
  const select = document.getElementById(`map-spots-${map}`);
  const selectedOption = select.options[select.selectedIndex];
  if (!selectedOption.value) return;
  try {
    const locationData = JSON.parse(selectedOption.dataset.location);
    const response = await fetch(`/api/locations/${map}/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ location: locationData })
    });
    if (!response.ok) throw new Error('Błąd zapisu spotu');
    const result = await response.json();
    document.getElementById('mapSpotsMsg').textContent = `Zapisano spot: ${locationData.id}`;
    await refreshMapSpotsTable();
  } catch (error) {
    document.getElementById('mapSpotsMsg').textContent = `Błąd: ${error.message}`;
  }
}

async function refreshMapSpotsTable() {
  const spotsTbody = document.getElementById('map-spots-table');
  if (!spotsTbody) return;
  const res = await fetch('/api/player_data', { cache: 'no-store' });
  if (!res.ok) return;
  const d = await res.json();
  const spots = d.player_data?.map_spots || {};
  spotsTbody.innerHTML = '';
  for (const [key, spot] of Object.entries(spots)) {
    spotsTbody.innerHTML += `<tr>
      <td>${key.replace('_map_spots','')}</td>
      <td>${spot.id ?? ''}</td>
      <td>${spot.moobs ?? ''}</td>
      <td>${spot.x ?? ''}</td>
      <td>${spot.y ?? ''}</td>
      <td>${spot.loc_x ?? ''}</td>
      <td>${spot.loc_y ?? ''}</td>
      <td>${spot.tolerance ?? ''}</td>
    </tr>`;
  }
}

document.addEventListener('DOMContentLoaded', function() {
  if (document.getElementById('map-spots-aida')) {
    window.loadAllMapSpots();
    refreshMapSpotsTable();
  }
});
// Minimal, robust front-end script for lazy-loading partials and wiring Map Levels
const $ = id => document.getElementById(id);

function setText(id, value) {
  const el = $(id);
  if (!el) return;
  el.textContent = value;
}

function setConnected(value) {
  const el = $('connected');
  if (!el) return;
  el.textContent = value ? 'YES' : 'NO';
  el.classList.remove('text-success','text-danger');
  el.classList.add(value ? 'text-success' : 'text-danger');
}

function pretty(obj) {
  try { return JSON.stringify(obj, null, 2); } catch { return String(obj); }
}

async function loadPartial(url, containerId) {
  const container = $(containerId);
  if (!container) return;
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) throw new Error(`Failed to load ${url}: HTTP ${res.status}`);
  container.innerHTML = await res.text();
}

async function refreshPlayer() {
  const pre = $('rawJson');
  if (!pre) return;
  try {
    const res = await fetch('/api/player_data', { cache: 'no-store' });
    if (!res.ok) throw new Error(res.statusText || res.status);
    const d = await res.json();
    // response may contain nested `player_data` or snapshot/state
    const src = d.player_data || d.snapshot?.state || d;
    setText('lastRefresh', new Date().toLocaleTimeString());
    setText('player', src.player ?? '-');
    setText('level', src.level ?? '-');
    setText('reset', src.reset ?? '-');
    setText('exppm', src.exp_per_minute ?? src.exp_per_minute ?? '-');
    setText('health', src.health ?? '-');
    setText('helperStatus', src.helper_status ?? '-');
    setText('pauseState', d.paused === true ? 'Paused' : (d.paused === false ? 'Running' : (src.pause_state ?? '-')));
    // Speedrun info
    const speedrunDiv = document.getElementById('speedrun');
    if (speedrunDiv) {
      const isIt = src.is_it_speedrun;
      const run = src.run_speedrun;
      speedrunDiv.textContent = `${isIt}`;
    }
    // get global pause status from /api/pause if available
    try {
      const p = await fetch('/api/pause', { cache: 'no-store' });
      if (p.ok) {
        const pj = await p.json();
        setText('pauseState', pj.paused ? 'Paused' : 'Running');
      }
    } catch (err) {
      // ignore; keep previous value
    }
    setText('location', src.location_name ?? '-');
    if (src.location_coord_x !== undefined && src.location_coord_y !== undefined) setText('coords', `${src.location_coord_x}, ${src.location_coord_y}`);
    setText('partyMode', src.player_in_party ?? 'Solo / Party / Independend');
    setText('zen', src.zen ?? '');
    setText('time', src.time ?? '-');
    setText('mouseRel', pretty(src.mouse_relative_pos ?? src.mouse_position ?? '-'));
    setConnected(!!src.connected);
    pre.textContent = pretty(d);
  } catch (e) {
    pre.textContent = `ERROR: ${e.message}`;
  }
}

async function boot() {
  try {
    await loadPartial('/static/partials/tab_live.html', 'tab-live-container');
    await refreshPlayer();
    setInterval(refreshPlayer, 2000);

    // lazy load actions
    const actionsBtn = document.querySelector('[data-bs-target="#tab-actions"]');
    if (actionsBtn) actionsBtn.addEventListener('shown.bs.tab', async () => {
      await loadPartial('/static/partials/tab_actions.html', 'tab-actions-container');
      try {
        if (typeof window !== 'undefined' && typeof window.wireActions === 'function') await window.wireActions();
        else if (typeof wireActions === 'function') await wireActions();
        else console.warn('wireActions not defined');
      } catch(e){ console.error('wireActions failed', e); }
    });

    // lazy load map levels
    const mapBtn = document.querySelector('[data-bs-target="#tab-map-levels"]');
    if (mapBtn) mapBtn.addEventListener('shown.bs.tab', async () => {
      await loadPartial('/static/partials/map_levels.html', 'tab-map-levels-container');
      try { await wireMapLevels(); } catch (e) { console.error('wireMapLevels failed', e); }
    });

    // lazy load map spots
    const mapSpotsBtn = document.querySelector('[data-bs-target="#tab-map-spots"]');
    if (mapSpotsBtn) mapSpotsBtn.addEventListener('shown.bs.tab', async () => {
      await loadPartial('/static/partials/map_spots.html', 'tab-map-spots-container');
      try { window.loadAllMapSpots(); } catch (e) { console.error('loadAllMapSpots failed', e); }
    });

  } catch (e) {
    console.error('boot error', e);
    const live = $('tab-live-container');
    if (live) live.textContent = `ERROR: ${e.message}`;
  }
}

boot();


// --- Map Spots loading ---
async function loadMapSpotsLocations(map) {
  const endpoints = {
    aida: '/api/locations/aida',
    atlans: '/api/locations/atlans',
    lacleon: '/api/locations/lacleon',
    icarus2: '/api/locations/icarus2',
  };
  const selectId = `map-spots-${map}`;
  try {
    const response = await fetch(endpoints[map]);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const locations = await response.json();
    const select = document.getElementById(selectId);
    if (!select) return;
    select.innerHTML = '<option value="">-- Choose an option --</option>';
    locations.forEach(location => {
      const option = document.createElement('option');
      option.value = location.id;
      option.textContent = `${location.id} - ${location.moobs}`;
      option.dataset.location = JSON.stringify(location);
      select.appendChild(option);
    });
  } catch (error) {
    const select = document.getElementById(selectId);
    if (select) select.innerHTML = '<option value="">Error loading options</option>';
  }
}

async function saveMapSpots(map) {
  const select = document.getElementById(`map-spots-${map}`);
  const selectedOption = select.options[select.selectedIndex];
  if (!selectedOption.value) return;
  try {
    const locationData = JSON.parse(selectedOption.dataset.location);
    const response = await fetch(`/api/locations/${map}/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ location: locationData })
    });
    if (!response.ok) throw new Error(`Save failed: ${response.status}`);
    const result = await response.json();
    console.log('Save result:', result);
  } catch (error) {
    console.error('Error saving location:', error);
  }
}

// Load all map spots dropdowns when partial loads
window.loadAllMapSpots = function() {
  loadMapSpotsLocations('aida');
  loadMapSpotsLocations('atlans');
  loadMapSpotsLocations('lacleon');
  loadMapSpotsLocations('icarus2');
}

// --- Map levels helpers ---
function createActiveRow(mapName, min=0, max=0, enabled=true) {
  const tr = document.createElement('tr');
  tr.dataset.map = mapName;
  tr.innerHTML = `
    <td class="fw-semibold">${mapName}</td>
    <td><input type="number" class="form-control form-control-sm min-level" value="${min}"></td>
    <td><input type="number" class="form-control form-control-sm max-level" value="${max}"></td>
    <td class="text-center"><input class="form-check-input map-enabled" type="checkbox" ${enabled ? 'checked' : ''}></td>
  `;
  return tr;
}

function createInactiveRow(mapName) {
  const tr = document.createElement('tr');
  tr.dataset.map = mapName;
  tr.innerHTML = `
    <td class="fw-semibold">${mapName}</td>
    <td class="text-center"><button class="btn btn-sm btn-outline-primary enable-map" data-map="${mapName}">Enable</button></td>
  `;
  return tr;
}

function collectMapLimitsFromDom() {
  const out = {};
  for (const tr of document.querySelectorAll('#map-level-table tr')) {
    const name = tr.dataset.map;
    const min = Number(tr.querySelector('.min-level')?.value ?? 0);
    const max = Number(tr.querySelector('.max-level')?.value ?? 0);
    const enabled = !!tr.querySelector('.map-enabled')?.checked;
    out[name] = { min, max, enabled };
  }
  for (const tr of document.querySelectorAll('#map-level-table-inactive tr')) {
    const name = tr.dataset.map;
    if (!(name in out)) out[name] = { min: 0, max: 0, enabled: false };
  }
  return out;
}

async function loadMapLimits() {
  const res = await fetch('/api/map-level-limits', { cache: 'no-store' });
  if (!res.ok) return {};
  return await res.json();
}

async function saveMapLimits(limits) {
  const res = await fetch('/api/map-level-limits', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ map_level_limits: limits })
  });
  if (!res.ok) throw new Error('save failed');
  return await res.json();
}

async function wireMapLevels() {
  const activeTbody = document.getElementById('map-level-table');
  const inactiveTbody = document.getElementById('map-level-table-inactive');
  const btnSave = document.getElementById('btn-save-levels');
  if (!activeTbody || !inactiveTbody || !btnSave) return;

  const limits = await loadMapLimits().catch(() => ({}));
  activeTbody.innerHTML = ''; inactiveTbody.innerHTML = '';

  // sort by min then name
  const names = Object.keys(limits).sort((a,b)=>{
    const A = limits[a]||{}; const B = limits[b]||{};
    const am = Number(A.min||0), bm = Number(B.min||0);
    if (am !== bm) return am - bm;
    return a.localeCompare(b);
  });

  for (const name of names) {
    const cfg = limits[name] || {};
    const enabled = !!cfg.enabled;
    if (enabled) activeTbody.appendChild(createActiveRow(name, cfg.min ?? 0, cfg.max ?? 0, true));
    else inactiveTbody.appendChild(createInactiveRow(name));
  }

  // enable from inactive
  inactiveTbody.addEventListener('click', (e) => {
    const btn = e.target.closest('.enable-map');
    if (!btn) return;
    const map = btn.dataset.map;
    const tr = btn.closest('tr'); if (tr) tr.remove();
    activeTbody.appendChild(createActiveRow(map, 0, 0, true));
  });

  // move to inactive when unchecked
  activeTbody.addEventListener('change', (e) => {
    if (!e.target.matches('.map-enabled')) return;
    const chk = e.target; const tr = chk.closest('tr'); if (!tr) return;
    if (!chk.checked) {
      const map = tr.dataset.map; tr.remove(); inactiveTbody.appendChild(createInactiveRow(map));
    }
  });

  btnSave.addEventListener('click', async () => {
    const msg = document.getElementById('mapLevelsMsg');
    try {
      const out = collectMapLimitsFromDom();
      await saveMapLimits(out);
      if (msg) { msg.textContent = 'Saved'; setTimeout(()=>msg.textContent='',1500); }
    } catch (e) { if (msg) msg.textContent = 'Save failed'; }
  });

  // --- MAP SPOTS TABLE ---
  const spotsTbody = document.getElementById('map-spots-table');
  if (spotsTbody) {
    spotsTbody.innerHTML = '';
    try {
      const res = await fetch('/api/player_data', { cache: 'no-store' });
      if (res.ok) {
        const data = await res.json();
        const mapSpots = data.map_spots || {};
        for (const [map, spot] of Object.entries(mapSpots)) {
          const tr = document.createElement('tr');
          tr.innerHTML = `
            <td>${map.replace('_map_spots','')}</td>
            <td>${spot.id ?? ''}</td>
            <td>${spot.moobs ?? ''}</td>
            <td>${spot.x ?? ''}</td>
            <td>${spot.y ?? ''}</td>
            <td>${spot.loc_x ?? ''}</td>
            <td>${spot.loc_y ?? ''}</td>
            <td>${spot.tolerance ?? ''}</td>
          `;
          spotsTbody.appendChild(tr);
        }
      }
    } catch (e) {
      spotsTbody.innerHTML = '<tr><td colspan="8">Błąd ładowania map_spots</td></tr>';
    }
  }
}

// --- Actions wiring ---
async function wireActions() {
  const btn = document.getElementById('btnTogglePause');
  const label = document.getElementById('pauseStateLabel');
  const sendBtn = document.getElementById('btnSendAction');
  const input = document.getElementById('actionInput');
  const previewBtn = document.getElementById('btnRefreshScreen');
  const previewImg = document.getElementById('screenPreview');
  const previewStatus = document.getElementById('screenPreviewStatus');
  if (!btn || !label) return;
  let current = null;

  async function refreshPause() {
    try {
      const res = await fetch('/api/pause', { cache: 'no-store' });
      if (!res.ok) return;
      const j = await res.json();
      current = !!j.paused;
      label.textContent = current ? 'Paused' : 'Running';
      label.classList.remove('text-success','text-danger');
      label.classList.add(current ? 'text-danger' : 'text-success');
      btn.textContent = current ? 'START' : 'PAUSE';
    } catch (e) {
      console.error('refreshPause failed', e);
    }
  }

  btn.addEventListener('click', async () => {
    try {
      const res = await fetch('/api/pause', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paused: !current })
      });
      if (!res.ok) throw new Error('request failed');
      const j = await res.json();
      current = !!j.paused;
      label.textContent = current ? 'Paused' : 'Running';
      label.classList.remove('text-success','text-danger');
      label.classList.add(current ? 'text-danger' : 'text-success');
      btn.textContent = current ? 'START' : 'PAUSE';
    } catch (e) {
      console.error('toggle pause failed', e);
    }
  });

  if (sendBtn && input) {
    sendBtn.addEventListener('click', async () => {
      const text = input.value.trim();
      if (!text) return;
      try {
        const res = await fetch('/api/send_message_ui', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text })
        });
        if (!res.ok) throw new Error('Send failed');
        input.value = '';
        // Optionally show a success message
      } catch (e) {
        console.error('Send message error', e);
      }
    });
  }

  async function refreshScreenPreview() {
    if (!previewImg) return;
    if (previewBtn) {
      previewBtn.disabled = true;
      previewBtn.textContent = 'Refreshing...';
    }
    if (previewStatus) previewStatus.textContent = 'Fetching preview...';
    try {
      const playerLabel = document.getElementById('player');
      const playerName = playerLabel ? playerLabel.textContent.trim() : '';
      const payload = {
        title: playerName ? `GoldMU || Player: ${playerName}` : 'GoldMU || Player:',
        rect: { x: 0, y: 0, w: 800, h: 630 }
      };
      const res = await fetch('/api/screen_preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error || 'Capture failed');
      const src = data.path || `/static/data/screen_preview.png?v=${Date.now()}`;
      previewImg.src = src.includes('v=') ? src : `${src}&cb=${Date.now()}`;
      if (previewStatus) previewStatus.textContent = 'Preview updated just now';
    } catch (e) {
      console.error('screen preview failed', e);
      if (previewStatus) previewStatus.textContent = `Error: ${e.message}`;
    } finally {
      if (previewBtn) {
        previewBtn.disabled = false;
        previewBtn.textContent = 'Refresh';
      }
    }
  }

  if (previewBtn) {
    previewBtn.addEventListener('click', refreshScreenPreview);
  }

  if (previewImg) {
    refreshScreenPreview();
  }

  await refreshPause();
}

