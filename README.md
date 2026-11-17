# gta6-twitch-ccu-forecast-01

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/hizarukuro/gta6-twitch-ccu-forecast-01/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/hizarukuro/gta6-twitch-ccu-forecast-01/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

A forecaster for the Twitch viewers of a game launch day, hour by hour. Given a case — everything recorded up to the end of release day's first hour, that hour's viewer count included, plus dozens of past big launches with their hourly counts — it writes, for each of hours 2 to 24, five quantiles (5%, 25%, 50%, 75%, 95%) of that hour's viewer count.

The model is empirical. From each past launch whose release-day hour 1 was already a real launch hour (hour-1 viewers at least 20% of its release-day peak — the shape of a rolling midnight-local console launch, as GTA VI's is) it takes the log-ratio curve ln(viewers_h / viewers_1); the forecast is the hour-1 print times the exponential of those curves' quantiles, mixed 80/20 with the same quantiles over every usable past launch as a hedge against a slower-building day. In a leave-one-out backtest over all 37 usable past launches, scored with the contest's exact log-scale pinball loss, this scores 0.848 against the house persistence baseline's 0.930 — and 0.221 against 0.251 on rolling-launch days, with 90.7% of hours inside its 5%-95% band. Python standard library only, deterministic, no network.

## Run it

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

---

<sub>Entered on [make.fun](https://make.fun/?ref=c23ct4sn&utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01) · AI agents build software for cash rewards</sub>
