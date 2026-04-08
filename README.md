# RhymeMapper

**RhymeMapper** is a Python tool for analyzing rhyme schemes in rap lyrics using phonetic data.  
It splits words into syllables, extracts phonetic features (nucleus and coda), and color‑codes rhyming syllables in the terminal output.

## Features

- Phonetic transcription using `g2p_en`
- Syllable splitting with `syllabify` (fallback heuristic for unknown words)
- Rhyme signature based on vowel nucleus and consonant coda
- Slant rhyme support via configurable consonant families
- Terminal output with ANSI colors for rhyming syllables
- Adjustable minimum occurrence threshold for rhyme groups

## Installation

```bash
git clone https://github.com/yourusername/RhymeMapper.git
cd RhymeMapper
python -m venv .venv
source .venv/bin/activate   # or `.venv\Scripts\activate` on Windows
pip install g2p_en syllabify
```

## Usage 
- Place your lyrics in a text file or modify the main.py entry point.
- run : python -m src.main
- The terminal will display the lyrics with rhyming syllables highlighted in different colors.

# Command‑line interface (planned)
Future versions may accept audio files and text inputs as arguments.

## Dependencies
    - Python 3.7+

    - g2p_en – phoneme conversion

    - syllabify – syllable splitting (uses CMU Pronouncing Dictionary)

#### Note: 
This README avoids hardcoded examples or specific output details, so it remains valid as the project evolves. It describes the core concepts and customization points without tying them to a particular version.

