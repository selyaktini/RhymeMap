# RhymeMapper

.PHONY: help install test test-offline stats plots demo web web-export serve karaoke eval gold lexicon tune clean all

PYTHON = python3
DATA_DIR = data
DATASET ?= dataset/artists_sample.csv

help:
	@echo "RhymeMapper:"
	@echo "  make install   Install dependencies and NLTK corpora"
	@echo "  make test      Run the unit tests"
	@echo "  make test-offline  Run them with the network blocked"
	@echo "  make demo      Colour-code the demo verse in the terminal"
	@echo "  make stats     Analyse a corpus -> $(DATA_DIR)/stats.csv"
	@echo "  make plots     Generate all figures into $(DATA_DIR)/"
	@echo "  make web       Export web/data.js and open the viewer"
	@echo "  make serve     Serve the viewer with live analysis of your own lyrics"
	@echo "  make karaoke   Export with word timings (AUDIO=... TIMINGS=...)"
	@echo "  make eval      Run the ablation and artist-ID experiments"
	@echo "  make gold      Rebuild eval/gold.json from the annotations"
	@echo "  make lexicon   Rebuild the Darija word list from the master CSV"
	@echo "  make clean     Remove caches and generated files"
	@echo "  make all       stats, plots, then demo"
	@echo ""
	@echo "  Override the corpus with: make stats DATASET=path/to.csv"

install:
	pip install -r requirements.txt
	# g2p_en declares `distance`, which cannot build against setuptools 60+.
	# It never imports it; its real dependencies are in requirements.txt.
	pip install --no-deps g2p_en
	$(PYTHON) -m scripts.fetch_nltk_data

test:
	./run_tests.sh

# Reduces dataset/darija_lexicon_master_150k.csv (61 MB of provenance) to the
# word list the engine actually reads. The output is committed, so this only
# needs re-running when the master changes.
lexicon:
	$(PYTHON) -m scripts.build_darija_lexicon

# The same suite with every outbound connection blocked, proving the song
# loader's network seams are really substituted rather than reaching out.
test-offline:
	$(PYTHON) -m scripts.check_no_network

stats:
	$(PYTHON) -m scripts.generate_stats --input $(DATASET)

plots:
	$(PYTHON) -m analysis.run_all_plots

demo:
	$(PYTHON) -m rhymemap.main --legend

web-export:
	$(PYTHON) -m rhymemap.webexport --input $(DATASET) --demo --engine chains

web: web-export
	@echo "Opening web/index.html"
	@$(PYTHON) -c "import pathlib, webbrowser; webbrowser.open(pathlib.Path('web/index.html').resolve().as_uri())" || \
		echo "Could not open a browser. Open web/index.html manually."

gold:
	$(PYTHON) -m eval.build_gold

serve: web-export
	$(PYTHON) -m scripts.serve_web

# Karaoke playback: needs an audio file in web/ and a word-timing file.
#   make karaoke AUDIO=track.mp3 TIMINGS=timings.json
karaoke:
	@test -n "$(TIMINGS)" || (echo "usage: make karaoke AUDIO=track.mp3 TIMINGS=timings.json" && exit 1)
	$(PYTHON) -m rhymemap.webexport --input $(DATASET) --demo --timings $(TIMINGS) --audio $(AUDIO)
	$(PYTHON) -m scripts.serve_web

eval: gold
	$(PYTHON) -m eval.ablation
	@echo ""
	$(PYTHON) -m eval.artist_id

tune:
	$(PYTHON) -m eval.tune

clean:
	rm -rf .cache
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	find . -name "*.pyc" -delete
	rm -f $(DATA_DIR)/stats.csv $(DATA_DIR)/*.png web/data.js

all: stats plots demo
