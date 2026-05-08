#!/usr/bin/env bash
# IndexNow submit — submit URLs from sitemap to Bing/Yandex/Seznam/Naver.
#
# Usage:
#   ./scripts/indexnow-submit.sh                 # submit ALL URLs in sitemap
#   ./scripts/indexnow-submit.sh url1 url2 ...   # submit specific URLs only
#
# Requires: curl, jq

set -euo pipefail

HOST="nctvtvn.fyi"
KEY="f5864ea3c1334249a6bdfa57bba29f9b"
KEY_LOCATION="https://${HOST}/${KEY}.txt"
SITEMAP_URL="https://${HOST}/sitemap.xml"
ENDPOINT="https://api.indexnow.org/indexnow"

# Verify the key file is accessible (IndexNow requires this).
echo "→ Verifying key file at ${KEY_LOCATION} ..."
remote_key=$(curl -fsSL "${KEY_LOCATION}" | tr -d '[:space:]') || {
  echo "✗ Key file not found at ${KEY_LOCATION}"
  echo "  Make sure static/${KEY}.txt is deployed."
  exit 1
}
if [[ "${remote_key}" != "${KEY}" ]]; then
  echo "✗ Key mismatch. Remote: '${remote_key}' Expected: '${KEY}'"
  exit 1
fi
echo "✓ Key verified"

# Build URL list.
if [[ $# -gt 0 ]]; then
  urls=("$@")
  echo "→ Using ${#urls[@]} URL(s) from arguments"
else
  echo "→ Fetching URLs from ${SITEMAP_URL} ..."
  mapfile -t urls < <(curl -fsSL "${SITEMAP_URL}" \
    | grep -oE '<loc>[^<]+</loc>' \
    | sed -E 's#</?loc>##g')
  echo "✓ Found ${#urls[@]} URL(s) in sitemap"
fi

if [[ ${#urls[@]} -eq 0 ]]; then
  echo "✗ No URLs to submit"
  exit 1
fi

# IndexNow accepts up to 10,000 URLs per request — chunk to be safe.
chunk_size=1000
total=${#urls[@]}
submitted=0

for ((i=0; i<total; i+=chunk_size)); do
  chunk=("${urls[@]:i:chunk_size}")
  payload=$(jq -n \
    --arg host "${HOST}" \
    --arg key "${KEY}" \
    --arg keyLocation "${KEY_LOCATION}" \
    --argjson urlList "$(printf '%s\n' "${chunk[@]}" | jq -R . | jq -s .)" \
    '{host: $host, key: $key, keyLocation: $keyLocation, urlList: $urlList}')

  echo "→ Submitting batch $((i/chunk_size + 1)) (${#chunk[@]} URLs) ..."
  http_code=$(curl -sS -o /tmp/indexnow_resp.txt -w '%{http_code}' \
    -X POST "${ENDPOINT}" \
    -H "Content-Type: application/json; charset=utf-8" \
    -d "${payload}")

  case "${http_code}" in
    200|202)
      echo "  ✓ ${http_code} — accepted"
      submitted=$((submitted + ${#chunk[@]}))
      ;;
    *)
      echo "  ✗ HTTP ${http_code}"
      cat /tmp/indexnow_resp.txt
      echo
      ;;
  esac
done

echo
echo "Done. Submitted ${submitted}/${total} URLs."
echo "Note: IndexNow forwards to Bing/Yandex/Seznam/Naver. Google does NOT use IndexNow."
echo "For Google, use Search Console → URL Inspection → Request Indexing."
