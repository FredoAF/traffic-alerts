# Traffic Alert

There is often a lot of traffic heading down the A5 from Towcester to Milton Keynes. This script runs as a k3s CronJob, asks Google for the current travel time, records it in Redis (which Grafana reads) and sends an ntfy notification when traffic is genuinely bad.

```
Google Distance Matrix ──► traffic-alert.py ──► Redis ──► Grafana
                                   └──► ntfy (only on real trouble)
```

## Redis keys

| Key | Type | Contents |
|---|---|---|
| `traffic_stats` | stream | One entry per run: `duration`, `baseline`, `delay`, `distance` (all seconds/metres), `day` (0 = Monday). History from the old TinyDB file was backfilled here and only has `duration` and `day`. |
| `traffic_latest` | hash | Most recent reading plus `text`, `level`, `updated`. For Grafana stat panels. |
| `traffic_alert` | hash | Alert state machine: `level`, `pending`, `streak`. Expires at midnight (Europe/London) so each day starts fresh. |
| `traffic_alerts` | stream | One entry per notification sent: `level`, `title`, `text`. Useful as Grafana annotations. |

## Alerting

Readings are classified against the delay over free-flow time:

| Level | Condition |
|---|---|
| terrible | Route distance > `DISTANCE_THRESHOLD` (Google has routed around the A5) |
| bad | Delay ≥ `BAD_DELAY` |
| normal | Delay < `CLEAR_DELAY` |
| (hold) | Between `CLEAR_DELAY` and `BAD_DELAY`: keep the current level |

A new level must be seen `CONFIRM_RUNS` times in a row before it is believed, and the gap between `CLEAR_DELAY` and `BAD_DELAY` stops readings that hover near the threshold from flapping. Notifications are only sent when the level gets worse (normal → bad, anything → terrible). Set `NOTIFY_CLEAR=1` to also get a "back to normal" message.

## Environment

| Variable | Default | Purpose |
|---|---|---|
| `API_KEY` | required | Google Maps API key |
| `REDIS_HOST` / `REDIS_PORT` | `localhost` / `6379` | Redis to write to |
| `NTFY_URL` | `https://ntfy.sh/towcestera5alerts` | Notification topic |
| `BAD_DELAY` | `600` | Seconds of delay that count as bad |
| `CLEAR_DELAY` | `300` | Seconds of delay below which an alert clears |
| `DISTANCE_THRESHOLD` | `9800` | Metres; longer means rerouted off the A5 |
| `CONFIRM_RUNS` | `2` | Consecutive readings to confirm a change |
| `NOTIFY_CLEAR` | `0` | `1` to notify when traffic returns to normal |

## Build and release

GitHub Actions builds the image on every push. Pushes to `main` publish `ghcr.io/fredoaf/traffic-alerts:edge`; publishing a GitHub release tagged `X.Y.Z` publishes `X.Y.Z`, `X.Y` and `X`. The CronJobs in `hubble/traffic/` pin an exact version, so bump them after each release.

`./build.sh` builds a local `traffic-alerts:dev` image and drops you into a shell in it for a smoke test against a port-forwarded Redis.
