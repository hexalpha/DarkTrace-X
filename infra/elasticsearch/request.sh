#!/bin/sh
set -eu
# A mounted CA selects verified HTTPS; failures never retry over HTTP.
if [ -f /usr/share/elasticsearch/config/certs/ca.crt ]; then
    base=https://localhost:9200
    set -- --cacert /usr/share/elasticsearch/config/certs/ca.crt "$@"
else
    base=http://localhost:9200
fi
exec curl --fail --silent --show-error --max-time 300 --user "elastic:$ELASTIC_PASSWORD" --url "$base$DARKTRACE_ES_PATH" "$@"
