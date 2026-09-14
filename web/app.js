/* RhymeMapper viewer.
 *
 * Rhyme colour is generated from the group label rather than picked from a list
 * of CSS classes. There is no upper bound on groups -- Rap God has 56 under the
 * exact engine and 257 under chain detection -- so an enumerated palette cannot
 * work, and the previous .rhyme-a ... .rhyme-z scheme silently reused colours.
 */

'use strict';

const verses = typeof rhymeData !== 'undefined' ? rhymeData.slice() : [];

const el = (id) => document.getElementById(id);
const ui = {
  threads: el('threads'), grain: el('grain'), waves: el('waves'), progress: el('progress'),
  progressBar: el('analyseProgress'),
  rotatingWord: el('rotatingWord'), heroLede: el('heroLede'),
  form: el('linkForm'), input: el('linkInput'), analyse: el('analyseBtn'),
  status: el('status'), pasteToggle: el('pasteToggle'), pastePanel: el('pastePanel'),
  lyricsInput: el('lyricsInput'), analysePaste: el('analysePasteBtn'), demo: el('demoBtn'),
  analysis: el('analysis'), lyrics: el('lyrics'), chains: el('chains'), stats: el('stats'),
  groupCount: el('groupCount'), tooltip: el('tooltip'),
  trackSelect: el('trackSelect'), engineSelect: el('engineSelect'), dimToggle: el('dimToggle'),
  trackTitle: el('trackTitle'), trackArtist: el('trackArtist'),
  trackCard: el('trackCard'), trackBadges: el('trackBadges'),
  player: el('player'), playerFrame: el('playerFrame'), audio: el('audio'),
  heroTitle: el('heroTitle'), heroParticles: el('heroParticles'),
  transport: el('transport'), seek: el('seek'), playToggle: el('playToggle'),
  playIcon: el('playIcon'), clock: el('clock'), playerNote: el('playerNote'),
};

let current = null;
let isolated = null;
let backdrop = null;
let wavesHandle = null;
let trackCard = null;
let stopStatusAnimation = null;

/* ------------------------------------------------------------- palette -- */

function hashLabel(label) {
  let hash = 0;
  for (let i = 0; i < label.length; i++) hash = (hash * 31 + label.charCodeAt(i)) % 100003;
  return hash;
}

/* Golden-angle stepping keeps adjacent groups far apart on the wheel. */
function hueFor(label) { return (hashLabel(label) * 137.508) % 360; }

function colourFor(label) {
  return `hsl(${hueFor(label).toFixed(1)}, ${70 + (hashLabel(label) % 9)}%, ${62 + (hashLabel(label + '~') % 13)}%)`;
}

/* ---------------------------------------------------------------- status -- */

function setStatus(text, kind = '') {
  if (stopStatusAnimation) { stopStatusAnimation(); stopStatusAnimation = null; }
  ui.status.className = `status ${kind}`;
  if (kind === 'working') {
    stopStatusAnimation = Effects.scrambleLoop(ui.status, text);
  } else {
    ui.status.textContent = text;
  }
}

/* ------------------------------------------------------------- rendering -- */

function renderStats(verse) {
  const m = verse.metrics || {};
  const cells = [
    ['Density', m.density ?? 0, '%', 1],
    ['Multisyllabic', m.multi ?? 0, '%', 1],
    ['Diversity', m.diversity ?? 0, '%', 1],
    ['Groups', m.signatures ?? 0, '', 0],
    ['Syllables', m.syllables ?? 0, '', 0],
  ];

  if (ui.stats.childElementCount !== cells.length) {
    ui.stats.innerHTML = cells.map(([name]) =>
      `<div class="stat"><span class="stat-value">0</span><span class="stat-name">${name}</span></div>`).join('');
  }
  ui.stats.querySelectorAll('.stat').forEach((node, i) => {
    if (!node.classList.contains('has-glare')) { Effects.glare(node); Effects.tilt(node); }
    const [name, value, suffix, decimals] = cells[i];
    node.querySelector('.stat-name').textContent = name;
    Effects.countUp(node.querySelector('.stat-value'), value, { suffix, decimals });
  });
}

function renderTrack(verse) {
  const title = verse.track || 'Untitled';
  const artist = verse.artist || '';
  // Kept in the DOM, visually hidden: the heading is inside the card's overlay,
  // but a page still needs a real heading for anything that reads structure.
  ui.trackTitle.textContent = title;
  ui.trackArtist.textContent = artist;

  const source = verse.source || {};
  const badges = [];
  if (verse.engine) badges.push({ text: verse.engine });

  // Where the words came from. A reader is entitled to know whether they are
  // looking at a human transcription or a machine's guess at someone rapping,
  // because it changes how much the rhyme analysis can be trusted.
  const PROVENANCE = {
    'captions': source.captions === 'automatic'
      ? { text: 'auto captions', hint: 'machine transcription - may mishear' }
      : { text: 'captions', hint: 'caption track published with the video' },
    'lrclib-synced': { text: 'LRCLIB synced', hint: 'community lyrics, timed per line' },
    'lrclib-plain': { text: 'LRCLIB', hint: 'community lyrics, no timing' },
    'pasted': { text: 'pasted', hint: 'your own text' },
  };
  const provenance = PROVENANCE[source.provider];
  if (provenance) badges.push(provenance);
  if (source.language) badges.push({ text: source.language });

  const SYNC = {
    word: { text: 'word sync', live: true, hint: 'a time for every word' },
    line: { text: 'line sync', live: true, hint: 'a time for every line' },
  };
  if (SYNC[source.sync]) badges.push(SYNC[source.sync]);
  else if (verse.timed) badges.push({ text: 'timed', live: true });

  const badgeHtml = badges
    .map((b) => `<span class="badge${b.live ? ' live' : ''}"${b.hint ? ` title="${b.hint}"` : ''}>${b.text}</span>`)
    .join('');
  ui.trackBadges.innerHTML = badgeHtml;

  if (!trackCard) trackCard = Effects.tiltedCard(ui.trackCard, { rotateAmplitude: 10 });
  trackCard.update({
    imageSrc: source.thumbnail || '',
    altText: source.thumbnail ? `${title} artwork` : '',
    captionText: artist ? `${artist} — ${title}` : title,
    overlayHtml:
      `<div class="tc-title">${escapeHtml(title)}</div>` +
      (artist ? `<div class="tc-artist">${escapeHtml(artist)}</div>` : '') +
      (badgeHtml ? `<div class="tc-badges">${badgeHtml}</div>` : ''),
  });
}

function renderLyrics(verse) {
  const fragment = document.createDocumentFragment();

  verse.lines.forEach((line, lineIndex) => {
    const lineEl = document.createElement('div');
    lineEl.className = 'line';
    lineEl.dataset.index = lineIndex;

    line.forEach((word) => {
      const wordEl = document.createElement('span');
      wordEl.className = 'word';

      word.syllables.forEach((syl) => {
        const node = document.createElement('span');
        node.textContent = syl.text;
        node.className = 'syllable ' + (syl.label ? 'rhyme' : 'plain');
        if (syl.label) {
          node.style.backgroundColor = colourFor(syl.label);
          node.dataset.label = syl.label;
        }
        if (syl.start !== null && syl.start !== undefined) {
          node.dataset.start = syl.start;
          node.dataset.end = syl.end;
        }
        node.dataset.nucleus = syl.nucleus || '';
        node.dataset.coda = syl.coda || '';
        node.dataset.onset = syl.onset || '';
        node.dataset.word = word.full_text || '';
        wordEl.appendChild(node);
      });
      lineEl.appendChild(wordEl);
      // A real space, not just the margin below. Without it the line is one
      // unbroken string in the DOM: copying lyrics off the page produced
      // "butimonlygoing...", and a screen reader read it as a single token.
      lineEl.appendChild(document.createTextNode(' '));
    });
    fragment.appendChild(lineEl);
  });

  ui.lyrics.innerHTML = '';
  if (!verse.lines.length) {
    ui.lyrics.innerHTML = '<p class="placeholder">Nothing to show.</p>';
    return;
  }

  // Words first, colour second: the reader sees the text, then the pattern.
  if (!Effects.prefersReducedMotion()) {
    ui.lyrics.classList.add('colouring');
    setTimeout(() => ui.lyrics.classList.remove('colouring'), 260);
  }
  ui.lyrics.appendChild(fragment);
}

function renderChains(verse) {
  const groups = verse.groups || [];
  ui.groupCount.textContent = groups.length ? `${groups.length}` : '';
  ui.chains.innerHTML = '';

  if (!groups.length) {
    ui.chains.innerHTML = '<p class="hint">No group passed the occurrence threshold.</p>';
    return;
  }

  groups.forEach((group) => {
    const row = document.createElement('button');
    row.type = 'button';
    row.className = 'chain';
    row.dataset.label = group.label;
    row.title = [
      group.rime ? `rime ${group.rime}` : '',
      group.similarity != null ? `similarity ${group.similarity}` : '',
      `strength ${group.strength}`,
    ].filter(Boolean).join(' · ');

    const size = group.length > 1
      ? `${group.length}<span class="unit">syl</span>×${group.occurrences}`
      : `${group.syllables}<span class="unit">syl</span>`;

    // Examples are what make a name legible: "-ames" means little until you
    // see flames / fame / shame beside it. A chain is named after one of its
    // own spans, so that span is dropped here rather than printed twice.
    const examples = (group.exemplars || [])
      .filter((word) => word !== group.label)
      .slice(0, 3)
      .join(' · ');

    row.innerHTML =
      `<span class="chain-swatch" style="background:${colourFor(group.label)}"></span>` +
      `<span class="chain-body">` +
        `<span class="chain-top">` +
          `<span class="chain-label">${escapeHtml(group.label)}</span>` +
          `<span class="chain-meta">${size}</span>` +
        `</span>` +
        (examples ? `<span class="chain-examples">${escapeHtml(examples)}</span>` : '') +
        positionMap(group) +
      `</span>`;

    row.addEventListener('click', () => toggleIsolate(group.label));
    ui.chains.appendChild(row);
  });
}

function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

/* Where a group falls across the verse, as a strip of ticks. Two groups with
 * the same count can be spread evenly or bunched into one passage, and that
 * difference is most of what a rhyme scheme *is* -- the count alone hides it. */
function positionMap(group) {
  const positions = group.positions || [];
  if (positions.length < 2) return '';
  const colour = colourFor(group.label);
  const ticks = positions
    .map((p) => `<i style="left:${(p * 100).toFixed(2)}%;background:${colour}"></i>`)
    .join('');
  return `<span class="chain-map" aria-hidden="true">${ticks}</span>`;
}

function show(verse) {
  current = verse;
  isolated = null;
  if (verse.engine) ui.engineSelect.value = verse.engine;

  ui.analysis.hidden = false;
  renderTrack(verse);
  renderStats(verse);
  renderLyrics(verse);
  renderChains(verse);
  applyIsolation();
  setupPlayback(verse);
  Effects.revealOnScroll();

  paintAmbience(verse);
}

/* The background reads the analysis: the denser the verse, the more energy in
 * the field behind it and the more swell in the waves. Extracted so switching
 * background re-applies the current verse rather than starting flat. */
function paintAmbience(verse) {
  const density = (verse.metrics?.density ?? 0) / 100;
  const strongest = (verse.groups || [])[0];
  const hue = strongest ? hueFor(strongest.label) : null;

  if (backdrop) {
    backdrop.setEnergy(0.22 + density * 0.6);
    if (hue !== null) backdrop.setHue(hue * 0.35);
  }
  if (wavesHandle) {
    wavesHandle.setLevel(0.14 + density * 0.5);
    if (hue !== null) wavesHandle.setHue(hue);
  }
}

/* ----------------------------------------------------------- interaction -- */

function syllablesWithLabel(label) {
  return ui.lyrics.querySelectorAll(`.syllable[data-label="${CSS.escape(label)}"]`);
}

function trace(label) {
  ui.lyrics.querySelectorAll('.syllable.traced').forEach((n) => n.classList.remove('traced'));
  if (!label) {
    if (!isolated) document.body.classList.remove('tracing');
    return;
  }
  syllablesWithLabel(label).forEach((n) => n.classList.add('traced'));
  document.body.classList.add('tracing');
}

function applyIsolation() {
  ui.chains.querySelectorAll('.chain').forEach((row) => {
    row.classList.toggle('active', row.dataset.label === isolated);
  });
  trace(isolated);
}

function toggleIsolate(label) {
  isolated = isolated === label ? null : label;
  applyIsolation();
}

function showTooltip(node, event) {
  const parts = [`<div class="tip-word">${node.dataset.word || node.textContent}</div>`];
  const phon = [];
  if (node.dataset.onset) phon.push(`onset ${node.dataset.onset}`);
  if (node.dataset.nucleus) phon.push(`nucleus ${node.dataset.nucleus}`);
  if (node.dataset.coda) phon.push(`coda ${node.dataset.coda}`);
  if (phon.length) parts.push(`<div class="tip-phon">${phon.join(' · ')}</div>`);

  if (node.dataset.label) {
    const group = (current?.groups || []).find((g) => g.label === node.dataset.label);
    let line = `group ${node.dataset.label}`;
    if (group) {
      line += group.length > 1
        ? ` — ${group.length} syllables ×${group.occurrences}`
        : ` — ${group.syllables} syllables`;
      if (group.similarity != null) line += `, similarity ${group.similarity}`;
    }
    parts.push(`<div class="tip-group">${line}</div>`);
  } else {
    parts.push('<div class="tip-none">no rhyme group</div>');
  }

  ui.tooltip.innerHTML = parts.join('');
  ui.tooltip.hidden = false;

  const pad = 14;
  const box = ui.tooltip.getBoundingClientRect();
  let x = event.clientX + pad;
  let y = event.clientY + pad;
  if (x + box.width > window.innerWidth - pad) x = event.clientX - box.width - pad;
  if (y + box.height > window.innerHeight - pad) y = event.clientY - box.height - pad;
  ui.tooltip.style.left = `${Math.max(pad, x)}px`;
  ui.tooltip.style.top = `${Math.max(pad, y)}px`;
}

/* -------------------------------------------------------------- playback -- */

let timed = [];
let playing = null;
let playingLine = null;
let timedLines = [];
let transport = null;      // the controller for whatever is currently playing
let seekSlider = null;
let clock = null;
let ticker = 0;
// The length the resolver reported. The player's own duration() is preferred
// once it has one, but an embed that is still loading - or blocked - reports 0,
// and a clock reading "0:16 / 0:00" is worse than no clock at all.
let knownDuration = 0;

function clearPlaying() {
  if (playing) { playing.node.classList.remove('playing'); playing = null; }
  if (playingLine) { playingLine.node.classList.remove('playing-line'); playingLine = null; }
}

/* One interface over two very different players.
 *
 * YouTube's iframe API is asynchronous, method-based and reports state through
 * callbacks; an <audio> element is synchronous and property-based. Everything
 * downstream - the scrubber, the clock, the highlight, click-to-seek - only
 * needs play/pause/seek/time/duration, so both are wrapped to provide exactly
 * that and nothing else has to know which is behind it. */

function youTubeController(videoId, onReady) {
  let player = null;
  let ready = false;

  ui.playerFrame.hidden = false;
  ui.playerFrame.innerHTML =
    `<iframe src="https://www.youtube-nocookie.com/embed/${encodeURIComponent(videoId)}?enablejsapi=1&rel=0"
             title="Track playback" allow="accelerometer; autoplay; encrypted-media; picture-in-picture"
             allowfullscreen loading="lazy"></iframe>`;

  const start = () => {
    const iframe = ui.playerFrame.querySelector('iframe');
    if (!iframe || !window.YT || !window.YT.Player) return;
    player = new window.YT.Player(iframe, {
      events: {
        onReady: () => { ready = true; onReady(); },
        onStateChange: () => refreshPlayButton(),
      },
    });
  };

  if (window.YT && window.YT.Player) {
    start();
  } else {
    if (!document.getElementById('yt-iframe-api')) {
      const script = document.createElement('script');
      script.id = 'yt-iframe-api';
      script.src = 'https://www.youtube.com/iframe_api';
      document.head.appendChild(script);
    }
    // The API calls this global once it has loaded.
    const previous = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = () => { if (previous) previous(); start(); };
  }

  const alive = () => ready && player && typeof player.getCurrentTime === 'function';

  return {
    kind: 'youtube',
    play() { if (alive()) player.playVideo(); },
    pause() { if (alive()) player.pauseVideo(); },
    seek(time) { if (alive()) player.seekTo(time, true); },
    time() { return alive() ? player.getCurrentTime() : 0; },
    duration() { return alive() ? player.getDuration() : 0; },
    isPlaying() { return alive() && player.getPlayerState() === 1; },
    setRate(rate) { if (alive() && player.setPlaybackRate) player.setPlaybackRate(rate); },
    destroy() {
      ready = false;
      if (player && player.destroy) { try { player.destroy(); } catch (_) { /* already gone */ } }
      player = null;
    },
  };
}

function audioController(src, onReady) {
  ui.audio.src = src;
  ui.audio.hidden = false;
  ui.audio.addEventListener('loadedmetadata', onReady, { once: true });

  // Removed again in destroy(). The <audio> element is shared across songs, so
  // listeners added per load would stack: after five songs the button would
  // refresh five times per state change.
  ui.audio.addEventListener('play', refreshPlayButton);
  ui.audio.addEventListener('pause', refreshPlayButton);

  return {
    kind: 'audio',
    play() { ui.audio.play().catch(() => {}); },
    pause() { ui.audio.pause(); },
    seek(time) { ui.audio.currentTime = time; },
    time() { return ui.audio.currentTime || 0; },
    duration() { return Number.isFinite(ui.audio.duration) ? ui.audio.duration : 0; },
    isPlaying() { return !ui.audio.paused; },
    setRate(rate) { ui.audio.playbackRate = rate; },
    destroy() {
      ui.audio.removeEventListener('play', refreshPlayButton);
      ui.audio.removeEventListener('pause', refreshPlayButton);
      ui.audio.pause();
      ui.audio.removeAttribute('src');
      ui.audio.load();
    },
  };
}

const PLAY_PATH = 'M8 5v14l11-7z';
const PAUSE_PATH = 'M6 5h4v14H6zM14 5h4v14h-4z';

function refreshPlayButton() {
  if (!transport) return;
  const playingNow = transport.isPlaying();
  ui.playIcon.firstElementChild.setAttribute('d', playingNow ? PAUSE_PATH : PLAY_PATH);
  ui.playToggle.setAttribute('aria-label', playingNow ? 'Pause' : 'Play');
}

function formatTime(seconds) {
  if (!Number.isFinite(seconds) || seconds < 0) seconds = 0;
  const total = Math.floor(seconds);
  const minutes = Math.floor(total / 60);
  return `${minutes}:${String(total % 60).padStart(2, '0')}`;
}

function teardownPlayback() {
  clearInterval(ticker);
  ticker = 0;
  clearPlaying();
  if (transport) { transport.destroy(); transport = null; }
  knownDuration = 0;
  if (seekSlider) { seekSlider.destroy(); seekSlider = null; }
  if (clock) { clock.destroy(); clock = null; }
  ui.playerFrame.hidden = true;
  ui.playerFrame.innerHTML = '';
  ui.audio.hidden = true;
  ui.player.hidden = true;
  ui.transport.hidden = true;
  ui.lyrics.classList.remove('seekable');
}

function setupPlayback(verse) {
  timed = [];
  timedLines = [];
  teardownPlayback();

  const source = verse.source || {};

  // Word-level: a time per syllable, from a caption track.
  timed = Array.from(ui.lyrics.querySelectorAll('.syllable[data-start]'))
    .map((node) => ({ node, start: +node.dataset.start, end: +node.dataset.end }))
    .sort((a, b) => a.start - b.start);

  // Line-level: a time per line, from a synced lyric. Coarser, and deliberately
  // not subdivided into words - splitting a line by word count would invent
  // timings that look exactly like measured ones.
  if (!timed.length && Array.isArray(source.line_times) && source.line_times.length) {
    const lineNodes = ui.lyrics.querySelectorAll('.line');
    timedLines = source.line_times
      .map((pair, index) => ({ node: lineNodes[index], start: +pair[0], end: +pair[1] }))
      .filter((item) => item.node)
      .sort((a, b) => a.start - b.start);
  }

  if (!timed.length && !timedLines.length) return;

  if (source.kind === 'youtube' && source.video_id) {
    // Embed YouTube's own player: playback stays on the platform licensed to
    // serve it, and nothing copyrighted is downloaded or hosted here.
    transport = youTubeController(source.video_id, onPlayerReady);
    ui.player.hidden = false;
  } else if (verse.audio) {
    transport = audioController(verse.audio, onPlayerReady);
    ui.player.hidden = false;
  } else {
    return;
  }

  mountTransport(source);
}

function mountTransport(source) {
  ui.transport.hidden = false;
  ui.lyrics.classList.add('seekable');

  knownDuration = source.duration || 0;
  seekSlider = Effects.elasticSlider(ui.seek, {
    label: 'Seek through the track',
    max: knownDuration,
    // While scrubbing, move the highlight with the thumb but do not touch the
    // player: seeking on every pointer move makes YouTube stutter badly.
    onInput: (value) => { paintClock(value); highlightAt(value); },
    onCommit: (value) => { if (transport) transport.seek(value); },
  });

  clock = Effects.splitFlap(ui.clock, `0:00 / ${formatTime(knownDuration)}`);

  ui.playerNote.textContent = timed.length
    ? 'Rhymes light up word by word. Click any line to jump there.'
    : 'Lyrics are timed per line. Click any line to jump there.';
}

function onPlayerReady() {
  refreshPlayButton();
  const total = totalDuration();
  if (total > 0 && seekSlider) seekSlider.setMax(total);

  clearInterval(ticker);
  ticker = setInterval(() => {
    if (!transport) return;
    const now = transport.time();
    if (seekSlider && !seekSlider.isScrubbing()) {
      seekSlider.setValue(now);
      paintClock(now);
      highlightAt(now);
    }
  }, 120);
}

function totalDuration() {
  const reported = transport ? transport.duration() : 0;
  return reported > 0 ? reported : knownDuration;
}

function paintClock(now) {
  if (!clock) return;
  clock.set(`${formatTime(now)} / ${formatTime(totalDuration())}`);
}

function togglePlay() {
  if (!transport) return;
  if (transport.isPlaying()) transport.pause();
  else transport.play();
  // YouTube reports the change through onStateChange; <audio> through events.
  setTimeout(refreshPlayButton, 120);
}

/* Clicking a line jumps the track to it. This is the pairing that makes the
 * analysis audible: see a rhyme, hear it. */
function seekToNode(node) {
  if (!transport) return;
  const line = node.closest('.line');
  const syllable = node.closest('.syllable[data-start]');

  let target = null;
  if (syllable) target = +syllable.dataset.start;
  else if (line) {
    const index = Number(line.dataset.index);
    const match = timedLines.find((item) => item.node === line)
      || timed.find((item) => item.node.closest('.line') === line);
    if (match) target = match.start;
    else if (Number.isFinite(index) && timedLines[index]) target = timedLines[index].start;
  }

  if (target === null || !Number.isFinite(target)) return;
  transport.seek(target);
  if (seekSlider) seekSlider.setValue(target);
  paintClock(target);
  highlightAt(target);
  if (!transport.isPlaying()) transport.play();
}

function seek(items, time) {
  // Binary search: this runs ~8x a second over up to 1500 syllables.
  let low = 0, high = items.length - 1;
  while (low <= high) {
    const mid = (low + high) >> 1;
    const item = items[mid];
    if (time < item.start) high = mid - 1;
    else if (time > item.end) low = mid + 1;
    else return item;
  }
  return null;
}

function reactTo(label) {
  if (label) {
    const hue = hueFor(label);
    if (backdrop) backdrop.setHue(hue * 0.4);
    if (wavesHandle) { wavesHandle.setHue(hue); wavesHandle.setLevel(0.72); }
  } else if (wavesHandle) {
    wavesHandle.setLevel(0.22);
  }
}

function highlightAt(time) {
  if (timed.length) { highlightSyllableAt(time); return; }
  highlightLineAt(time);
}

function highlightSyllableAt(time) {
  const found = seek(timed, time);
  if (found === playing) return;
  clearPlaying();
  if (found) {
    found.node.classList.add('playing');
    found.node.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    playing = found;
    reactTo(found.node.dataset.label);
  }
}

function highlightLineAt(time) {
  const found = seek(timedLines, time);
  if (found === playingLine) return;
  clearPlaying();
  if (found) {
    found.node.classList.add('playing-line');
    found.node.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    playingLine = found;
    // The line's own colour: whichever rhyme group it carries most of.
    const counts = new Map();
    found.node.querySelectorAll('.syllable[data-label]').forEach((node) => {
      counts.set(node.dataset.label, (counts.get(node.dataset.label) || 0) + 1);
    });
    let best = '', bestCount = 0;
    counts.forEach((count, label) => { if (count > bestCount) { best = label; bestCount = count; } });
    reactTo(best);
  }
}


/* ---------------------------------------------------------------- server -- */

const overHttp = () => location.protocol === 'http:' || location.protocol === 'https:';

async function post(path, body) {
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const payload = await response.json().catch(() => ({ error: `HTTP ${response.status}` }));
  if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
  return payload;
}

/* The static build (GitHub Pages) ships pre-analysed songs but has no analysis
 * backend, so live analysis is unavailable there. It is flagged by a global the
 * build step writes into data.js, rather than guessed from the protocol -- the
 * page is served over https in both cases. */
function requireServer() {
  if (overHttp()) return true;
  setStatus('Analysing needs the local server — run `make serve`.', 'error');
  return false;
}

function addVerse(payload) {
  verses.unshift(payload);
  populateTracks();
  ui.trackSelect.value = '0';
  show(payload);
  document.getElementById('analysis').scrollIntoView({ block: 'start' });
}

/* Read a newline-delimited JSON stream, handing each event to `onEvent`.
 *
 * The server reports what it has finished rather than how long it has been
 * going, so the percentage this drives is measured work: the resolve step moves
 * it when a step completes, and the analysis moves it per line, which is where
 * the time actually goes. */
async function postStream(path, body, onEvent) {
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...body, stream: true }),
  });
  if (!response.ok || !response.body) {
    // No stream available: fall back to the plain request, which still works.
    return post(path, body);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let result = null;

  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // A chunk can split a line in half; keep the remainder for the next one.
    const lines = buffer.split('\n');
    buffer = lines.pop();
    for (const line of lines) {
      if (!line.trim()) continue;
      let event;
      try { event = JSON.parse(line); } catch (_) { continue; }
      if (event.error) throw new Error(event.error);
      if (event.done) { result = event.payload; continue; }
      onEvent(event);
    }
  }

  if (!result) throw new Error('The analysis ended without returning anything.');
  return result;
}

function setProgress(fraction, stage) {
  const percent = Math.round(Math.min(1, Math.max(0, fraction)) * 100);
  ui.progressBar.hidden = false;
  ui.progressBar.style.setProperty('--done', String(fraction));
  ui.progressBar.setAttribute('aria-valuenow', String(percent));
  // Plain text, not scrambled: a number people are watching should be readable.
  if (stopStatusAnimation) { stopStatusAnimation(); stopStatusAnimation = null; }
  ui.status.className = 'status working';
  ui.status.textContent = `${percent}% · ${stage}`;
}

function clearProgress() {
  ui.progressBar.hidden = true;
  ui.progressBar.style.setProperty('--done', '0');
}

async function analyseLink(query) {
  if (!query.trim()) { setStatus('Paste a link first.', 'error'); return; }
  if (!requireServer()) return;

  ui.analyse.disabled = true;
  setProgress(0, 'starting');
  try {
    const payload = await postStream(
      '/api/song',
      { url: query.trim(), engine: ui.engineSelect.value },
      (event) => setProgress(event.progress ?? 0, event.stage || 'working'));
    addVerse(payload);
    setStatus(`${payload.artist} — ${payload.track}: ${payload.metrics.syllables} syllables, ${payload.metrics.signatures} rhyme groups.${languageNote(payload)}`);
  } catch (error) {
    setStatus(String(error.message || error), 'error');
  } finally {
    clearProgress();
    ui.analyse.disabled = false;
  }
}

/* The engine reads Moroccan Darija as well as English, and which one it chose
   changes every phoneme underneath the colours. Say so when it is not English,
   so nobody has to wonder whether the groups on screen mean anything. */
function languageNote(payload) {
  return payload?.language === 'dar' ? ' Read as Moroccan Darija.' : '';
}

async function analysePasted() {
  const lyrics = ui.lyricsInput.value.trim();
  if (!lyrics) { setStatus('Paste some lyrics first.', 'error'); return; }
  if (!requireServer()) return;

  ui.analysePaste.disabled = true;
  setStatus('Sounding it out…', 'working');
  try {
    const payload = await post('/api/analyze', { lyrics, engine: ui.engineSelect.value });
    addVerse(payload);
    setStatus(`${payload.metrics.syllables} syllables, ${payload.metrics.signatures} rhyme groups.${languageNote(payload)}`);
  } catch (error) {
    setStatus(String(error.message || error), 'error');
  } finally {
    ui.analysePaste.disabled = false;
  }
}

async function reanalyseCurrent() {
  if (!current?.text) return;
  if (!overHttp()) { ui.engineSelect.value = current.engine; return; }

  const index = verses.indexOf(current);
  setStatus(`Re-analysing with ${ui.engineSelect.value}…`, 'working');
  try {
    const payload = await post('/api/analyze', {
      lyrics: current.text, artist: current.artist,
      track: current.track, engine: ui.engineSelect.value,
    });
    // Re-analysis loses provenance, so carry it across.
    payload.source = current.source;
    if (index >= 0) verses[index] = payload;
    Effects.swap(() => show(payload));
    setStatus(`${payload.engine}: ${payload.metrics.density}% density, ${payload.metrics.signatures} groups.${languageNote(payload)}`);
  } catch (error) {
    setStatus(String(error.message || error), 'error');
    ui.engineSelect.value = current.engine;
  }
}

/* ----------------------------------------------------------------- wiring -- */

function populateTracks() {
  ui.trackSelect.innerHTML = '';
  verses.forEach((verse, i) => {
    const option = document.createElement('option');
    option.value = String(i);
    option.textContent = `${verse.artist} — ${verse.track}`;
    ui.trackSelect.appendChild(option);
  });
}

/* Decoration must never take the page down with it.
 *
 * Every effect below used to run unguarded in init(). One throw - a canvas
 * context refused, a WebGL call rejected, a browser missing something - and
 * everything after it was skipped, including the line that renders the
 * analysis. The page then showed a hero, a footer, and nothing in between,
 * with no clue why. The product is the analysis; the effects are decoration,
 * and decoration that fails should fail alone and quietly. */
function decorate(name, run) {
  try {
    return run();
  } catch (error) {
    console.error(`effect "${name}" failed and was skipped:`, error);
    return null;
  }
}

function init() {
  document.body.classList.add('dim');

  decorate('waves', () => { wavesHandle = Effects.waves(ui.waves); });

  // The aurora: drifting spectral light on a 2D canvas, hue taken from the rhyme
  // group under the playhead. The WebGL weave that briefly replaced it needed a
  // GPU to be worth having and looked worse than this when it did not get one.
  decorate('background', () => {
    backdrop = Effects.aurora(ui.threads);
    Effects.noise(ui.grain);
  });

  // The headline assembles out of particles, then hands back to the real <h1>.
  // splitText is the fallback: it is what runs under prefers-reduced-motion,
  // where the particle flight is suppressed.
  decorate('headline', () => {
    if (Effects.prefersReducedMotion()) {
      Effects.splitText(ui.heroTitle);
    } else {
      requestAnimationFrame(() =>
        decorate('particleText', () => Effects.particleText(ui.heroTitle, ui.heroParticles)));
    }
  });

  decorate('borderGlow', () =>
    document.querySelectorAll('.panel').forEach((panel) => Effects.borderGlow(panel)));
  decorate('profileCards', () => {
    document.querySelectorAll('[data-profile]').forEach((card) => {
      Effects.tilt(card, 8);
      Effects.glare(card);
    });
  });
  // Fall back to the initial rather than a broken-image icon.
  document.querySelectorAll('.profile-avatar').forEach((img) => {
    img.addEventListener('error', () => { img.hidden = true; });
  });
  decorate('clickSpark', () => Effects.clickSpark(document.body));
  decorate('magnet', () => Effects.magnet(ui.analyse));
  decorate('scrollProgress', () => Effects.scrollProgress(ui.progress));
  decorate('rotatingText', () => Effects.rotatingText(ui.rotatingWord,
    ['multisyllabic chains', 'slant rhymes', 'internal rhyme', 'assonance']));
  decorate('spotlight', () => document.querySelectorAll('.panel').forEach(Effects.spotlight));
  decorate('statTiles', () =>
    document.querySelectorAll('.stat').forEach((node) => { Effects.glare(node); Effects.tilt(node); }));
  ui.lyrics.classList.add('fade-foot');
  decorate('reveal', () => Effects.revealOnScroll());

  ui.form.addEventListener('submit', (event) => {
    event.preventDefault();
    analyseLink(ui.input.value);
  });

  ui.pasteToggle.addEventListener('click', () => {
    ui.pastePanel.hidden = !ui.pastePanel.hidden;
    if (!ui.pastePanel.hidden) ui.lyricsInput.focus();
  });
  ui.analysePaste.addEventListener('click', analysePasted);
  ui.lyricsInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) analysePasted();
  });

  ui.demo.addEventListener('click', () => {
    if (verses.length) {
      ui.trackSelect.value = '0';
      show(verses[0]);
      ui.analysis.scrollIntoView({ block: 'start' });
      setStatus('');
    } else {
      setStatus('No pre-analysed verses bundled — run `make web` first.', 'error');
    }
  });

  ui.lyrics.addEventListener('mouseover', (event) => {
    const node = event.target.closest('.syllable');
    if (!node) return;
    showTooltip(node, event);
    if (!isolated && node.dataset.label) trace(node.dataset.label);
  });
  ui.lyrics.addEventListener('mousemove', (event) => {
    if (ui.tooltip.hidden) return;
    const node = event.target.closest('.syllable');
    if (node) showTooltip(node, event);
  });
  ui.lyrics.addEventListener('mouseleave', () => {
    ui.tooltip.hidden = true;
    if (!isolated) trace(null);
  });
  ui.lyrics.addEventListener('click', (event) => {
    // A labelled syllable isolates its rhyme group; anywhere else on a line
    // seeks the track there. Both stay reachable: the sidebar isolates too, and
    // most of a line is not a labelled syllable.
    const node = event.target.closest('.syllable[data-label]');
    if (node) { toggleIsolate(node.dataset.label); return; }
    if (ui.lyrics.classList.contains('seekable')) seekToNode(event.target);
  });

  ui.trackSelect.addEventListener('change', (event) => {
    const verse = verses[+event.target.value];
    if (verse) show(verse);
  });
  ui.engineSelect.addEventListener('change', () => {
    if (current && current.engine !== ui.engineSelect.value) reanalyseCurrent();
  });

  ui.dimToggle.addEventListener('click', () => {
    const on = document.body.classList.toggle('dim');
    ui.dimToggle.setAttribute('aria-pressed', String(on));
  });

  ui.playToggle.addEventListener('click', togglePlay);

  ui.transport.querySelectorAll('.rate-btn').forEach((button) => {
    button.addEventListener('click', () => {
      const rate = Number(button.dataset.rate);
      if (transport) transport.setRate(rate);
      ui.transport.querySelectorAll('.rate-btn').forEach((other) => {
        other.setAttribute('aria-pressed', String(other === button));
      });
    });
  });

  // Space plays and pauses, the way every media player does - but never while
  // someone is typing a link or pasting lyrics.
  document.addEventListener('keydown', (event) => {
    if (event.code !== 'Space' || !transport) return;
    const tag = (event.target.tagName || '').toLowerCase();
    if (tag === 'input' || tag === 'textarea' || tag === 'button' || event.target.isContentEditable) return;
    event.preventDefault();
    togglePlay();
  });



  ['timeupdate', 'seeked', 'loadedmetadata'].forEach((event) => {
    ui.audio.addEventListener(event, () => { if (timed.length) highlightAt(ui.audio.currentTime); });
  });
  ui.audio.addEventListener('ended', clearPlaying);

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && isolated) toggleIsolate(isolated);
  });

  window.addEventListener('scroll', () => {
    const box = ui.lyrics.getBoundingClientRect();
    ui.lyrics.style.setProperty('--foot-on', box.bottom < window.innerHeight + 40 ? '0' : '1');
  }, { passive: true });

  if (verses.length) {
    populateTracks();
    show(verses[0]);
  } else {
    // data.js is generated, not committed. If it is missing the page has no
    // songs and used to render an empty shell in silence - a hero, a footer,
    // and nothing in between. Say what happened instead.
    ui.trackSelect.innerHTML = '<option>nothing bundled</option>';
    setStatus(
      window.rhymeDataMissing
        ? 'The bundled songs did not load (data.js is missing). Paste a link or some lyrics — that still works.'
        : 'No songs are bundled in this build. Paste a link or some lyrics to analyse one.',
      'warn');
  }
}

document.addEventListener('DOMContentLoaded', init);
