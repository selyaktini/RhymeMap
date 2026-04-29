let currentVerse = null;
let showAllSyllables = false;
let activeHighlightLabel = null;   // label actuellement surligné (null = aucun)

// Remplit la liste déroulante et initialise
function populateSelect() {
  const select = document.getElementById('trackSelect');
  select.innerHTML = '<option value="">-- Choisir un morceau --</option>';
  rhymeData.forEach((verse, idx) => {
    const option = document.createElement('option');
    option.value = idx;
    option.textContent = `${verse.artist} – ${verse.track}`;
    select.appendChild(option);
  });
  select.addEventListener('change', onTrackChange);
}

function onTrackChange(e) {
  const idx = e.target.value;
  if (idx === "") {
    currentVerse = null;
    activeHighlightLabel = null;
    document.getElementById('lyricsContainer').innerHTML =
      '<p class="placeholder">Sélectionnez un morceau pour commencer.</p>';
    clearGroupButtons();
    return;
  }
  currentVerse = rhymeData[idx];
  activeHighlightLabel = null;
  renderVerse();
}

// Récupère tous les labels uniques du morceau courant
function collectUniqueLabels() {
  if (!currentVerse) return [];
  const labels = new Set();
  currentVerse.lines.forEach(line => {
    line.forEach(word => {
      word.syllables.forEach(syl => {
        if (syl.label) labels.add(syl.label);
      });
    });
  });
  // Trie par ordre alphabétique
  return Array.from(labels).sort();
}

// Génère les boutons de groupes dans #groupButtons
function updateGroupButtons() {
  const container = document.getElementById('groupButtons');
  container.innerHTML = '';
  const labels = collectUniqueLabels();
  if (labels.length === 0) return;

  labels.forEach(label => {
    const btn = document.createElement('button');
    btn.textContent = label;
    btn.className = 'group-btn';
    if (label === activeHighlightLabel) {
      btn.classList.add('active');
    }
    btn.addEventListener('click', () => highlightGroup(label));
    container.appendChild(btn);
  });
}

function clearGroupButtons() {
  document.getElementById('groupButtons').innerHTML = '';
}

// Active/désactive le surlignage d'un groupe
function highlightGroup(label) {
  if (activeHighlightLabel === label) {
    // Désactive le surlignage
    activeHighlightLabel = null;
  } else {
    activeHighlightLabel = label;
  }
  renderVerse();
}

function renderVerse() {
  if (!currentVerse) return;
  const container = document.getElementById('lyricsContainer');
  container.innerHTML = '';

  currentVerse.lines.forEach(line => {
    const lineDiv = document.createElement('div');
    lineDiv.className = 'line';

    line.forEach(word => {
      const wordSpan = document.createElement('span');
      wordSpan.className = 'word';

      word.syllables.forEach(syl => {
        const sylSpan = document.createElement('span');
        sylSpan.textContent = syl.text;
        sylSpan.className = 'syllable';

        if (syl.label) {
          // La lettre est toujours en majuscule dans data.js (ex: "A")
          sylSpan.classList.add(`rhyme-${syl.label.toLowerCase()}`);
        } else {
          sylSpan.classList.add('no-rhyme');
        }

        // Visibilité selon le mode
        if (!showAllSyllables && !syl.label) {
          sylSpan.style.opacity = '0.4';
        } else {
          sylSpan.style.opacity = '1';
        }

        // Surlignage du groupe actif
        if (activeHighlightLabel && syl.label === activeHighlightLabel) {
          sylSpan.classList.add('highlight-group');
        }

        wordSpan.appendChild(sylSpan);
      });

      lineDiv.appendChild(wordSpan);
    });

    container.appendChild(lineDiv);
  });

  // Met à jour les boutons de groupes
  updateGroupButtons();
}

function toggleAllSyllables() {
  showAllSyllables = !showAllSyllables;
  const btn = document.getElementById('toggleRhymes');
  btn.textContent = showAllSyllables
    ? 'Masquer les syllabes non rimées'
    : 'Afficher toutes les syllabes';
  renderVerse();
}

// Initialisation
document.addEventListener('DOMContentLoaded', () => {
  populateSelect();
  document.getElementById('toggleRhymes').addEventListener('click', toggleAllSyllables);
});