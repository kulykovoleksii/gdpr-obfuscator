#!/usr/bin/env bash
set -euo pipefail

rm -rf package function.zip
mkdir -p package

# install dependencies into package
# requirements-runtime.txt is expected to be minimal or empty for MVP
python -m pip install -r requirements-runtime.txt -t package/

# copy source
cp -r src/gdpr_obfuscator package/

# create zip
cd package
zip -r ../function.zip . -q
cd ..

# size check
if command -v stat >/dev/null 2>&1; then
  SIZE_BYTES=$(stat -c%s function.zip 2>/dev/null || stat -f%z function.zip)
else
  SIZE_BYTES=$(python - <<PY
import os
print(os.path.getsize("function.zip"))
PY
)
fi

SIZE_MB=$((SIZE_BYTES / 1024 / 1024))
echo "Lambda package size: ${SIZE_MB} MB"

if [ $SIZE_MB -gt 50 ]; then
  echo "Package > 50MB (direct upload). Consider layer or S3 deploy"
  exit 1
fi

echo "Package size OK"
echo "Lambda package 'function.zip' is ready."