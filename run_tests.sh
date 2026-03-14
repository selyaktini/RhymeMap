#!/bin/bash

echo "Running unit tests for RhymeMapper..."
echo "==================================="

python -m unittest discover -s tests -p "test_*.py" -v

RESULT=$?

echo "==================================="
if [ $RESULT -eq 0 ]; then
  echo "✅ All tests passed!"
else
  echo "❌ Some tests failed."
fi

exit $RESULT
