# Cache, Rate-Limit, and Failure Behavior

## Cache hierarchy

1. In-memory TTL cache
2. Persistent compressed JSON cache
3. Live provider request
4. Stale cached fallback when the provider is unavailable or rate-limited

## Offline mode

Offline mode never contacts the live weather provider. A fresh or stale cached result can be served and is explicitly marked with:

- `offline_cache: true`
- `served_from_cache: true`
- `live_provider_contacted: false`
- `is_stale` reflecting whether the stale fallback window was used

If no cached result exists, the API returns a clear provider-unavailable error.

## HTTP 429 behavior

A provider rate limit activates a cooldown. During cooldown:

- A valid stale cache is served with stale metadata.
- Without cache, the API returns a rate-limit error.
- Repeated user refreshes should be avoided until cooldown expires.

## No fabricated fallback

The weather subsystem does not generate synthetic values to conceal provider failure. Long-term simulated weather is a separate, labeled engine.
