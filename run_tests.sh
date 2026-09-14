#!/bin/bash
# Run the RhymeMapper test suite from the project root.
set -u

echo "Running RhymeMapper tests"
echo "========================="

# -t . makes the project root the top-level import dir, so `src` and `tests`
# both import normally and no test file needs to patch sys.path.
python3 -m unittest discover -s tests -t . -p "test_*.py" -v
RESULT=$?

echo "========================="
if [ $RESULT -eq 0 ]; then
  echo "All tests passed."
else
  echo "Some tests failed."
fi
exit $RESULT
