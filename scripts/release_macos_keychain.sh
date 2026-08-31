#!/bin/sh
# Import Developer ID material into an ephemeral keychain and write the API key.
# Does not print certificate, password, or .p8 contents.
set -eu

fail_missing() {
  echo "Missing required GitHub secret $1. Tag releases fail closed." >&2
  exit 1
}

[ -n "${APPLE_CERTIFICATE:-}" ] || fail_missing APPLE_CERTIFICATE
[ -n "${APPLE_CERTIFICATE_PASSWORD:-}" ] || fail_missing APPLE_CERTIFICATE_PASSWORD
[ -n "${APPLE_SIGNING_IDENTITY:-}" ] || fail_missing APPLE_SIGNING_IDENTITY
[ -n "${APPLE_API_KEY:-}" ] || fail_missing APPLE_API_KEY
[ -n "${APPLE_API_ISSUER:-}" ] || fail_missing APPLE_API_ISSUER
[ -n "${APPLE_API_KEY_P8:-}" ] || fail_missing APPLE_API_KEY_P8
[ -n "${RUNNER_TEMP:-}" ] || {
  echo "RUNNER_TEMP is required" >&2
  exit 1
}
[ -n "${GITHUB_ENV:-}" ] || {
  echo "GITHUB_ENV is required" >&2
  exit 1
}

SIGN_DIR="${RUNNER_TEMP}/memovi-macos-signing"
mkdir -p "${SIGN_DIR}"
chmod 700 "${SIGN_DIR}"

CERT_P12="${SIGN_DIR}/certificate.p12"
B64_FILE="${SIGN_DIR}/certificate.b64"
KEYCHAIN_PATH="${SIGN_DIR}/build.keychain-db"
API_KEY_PATH="${SIGN_DIR}/AuthKey_${APPLE_API_KEY}.p8"

# shellcheck disable=SC2059
printf '%s' "${APPLE_CERTIFICATE}" >"${B64_FILE}"
openssl base64 -d -A -in "${B64_FILE}" -out "${CERT_P12}" 2>/dev/null || \
  openssl base64 -d -in "${B64_FILE}" -out "${CERT_P12}"
rm -f "${B64_FILE}"

KEYCHAIN_PASSWORD="$(openssl rand -base64 32)"
security create-keychain -p "${KEYCHAIN_PASSWORD}" "${KEYCHAIN_PATH}"
security set-keychain-settings -lut 21600 "${KEYCHAIN_PATH}"
security unlock-keychain -p "${KEYCHAIN_PASSWORD}" "${KEYCHAIN_PATH}"
security import "${CERT_P12}" -k "${KEYCHAIN_PATH}" -P "${APPLE_CERTIFICATE_PASSWORD}" \
  -T /usr/bin/codesign -T /usr/bin/security >/dev/null
rm -f "${CERT_P12}"
security set-key-partition-list -S apple-tool:,apple:,codesign: -s -k "${KEYCHAIN_PASSWORD}" \
  "${KEYCHAIN_PATH}" >/dev/null
security list-keychains -d user -s "${KEYCHAIN_PATH}"
security default-keychain -s "${KEYCHAIN_PATH}"
security unlock-keychain -p "${KEYCHAIN_PASSWORD}" "${KEYCHAIN_PATH}"

if ! security find-identity -v -p codesigning "${KEYCHAIN_PATH}" | grep -q "Developer ID Application"; then
  echo "Ephemeral keychain has no Developer ID Application identity." >&2
  exit 1
fi

# shellcheck disable=SC2059
printf '%s\n' "${APPLE_API_KEY_P8}" >"${API_KEY_PATH}"
chmod 600 "${API_KEY_PATH}"

{
  echo "APPLE_API_KEY_PATH=${API_KEY_PATH}"
  echo "MACOS_KEYCHAIN_PATH=${KEYCHAIN_PATH}"
} >>"${GITHUB_ENV}"

echo "Imported Developer ID certificate into an ephemeral keychain (identity not printed)."
