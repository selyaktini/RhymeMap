# Makefile for RhymeMapper

.PHONY: help install test stats plots demo clean

PYTHON = python3

# Directories
SRC_DIR = src
SCRIPT_DIR = scripts
ANALYSIS_DIR = analysis
DATA_DIR = data
DATASET_DIR = dataset

# Default target
help:
	@echo "RhymeMapper - Makefile commands:"
	@echo "  make install   Install dependencies (requires pip)"
	@echo "  make test      Run unit tests"
	@echo "  make stats     Generate statistics CSV (data/stats.csv)"
	@echo "  make plots     Generate all analysis plots (scatter, boxplot, heatmaps)"
	@echo "  make demo      Run the main demo (Eminem example)"
	@echo "  make clean     Remove generated files (__pycache__, figures, stats)"
	@echo "  make all       Run stats, plots, and demo in sequence"

install:
	pip install -r requirements.txt

test:
	./run_tests.sh

stats:
	$(PYTHON) -m scripts.generate_stats

plots:
	$(PYTHON) -m analysis.run_all_plots

demo:
	$(PYTHON) -m src.main
	$(PYTHON) -m export_for_web
	firefox web/index.html &

clean:
	rm -rf $(SRC_DIR)/__pycache__ $(ANALYSIS_DIR)/__pycache__ $(SCRIPT_DIR)/__pycache__ tests/__pycache__
	rm -f $(DATA_DIR)/stats.csv
	rm -f $(DATA_DIR)/*.png
	find . -name "*.pyc" -delete

all: stats plots demo
