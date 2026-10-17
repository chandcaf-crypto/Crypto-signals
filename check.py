import os, re, time, ccxt, requests, pandas as pd, numpy as np, ta
TOPIC = os.environ["NTFY_TOPIC"]
coin = re.sub(r"[^A-Z0-9]", "", os.environ.get("COIN","BTC").upper().split("/")[0].split(",")[0].strip())
coin = re.sub(r"(USDT|USDC|USD)$", "", coin) or coin
today = int(time.time()//86400)*86400000
since = int(time.time()*1000) - 300*86400000
def get(name, sym): e = getattr(ccxt, name)(); e.load_markets(); s = next(x for x in [sym+'/USD', sym+'/USDT', sym+'/USDC'] if x in e.symbols); d = pd.DataFrame(e.fetch_ohlcv(s,'1d',since=since,limit=300), columns=['t','o','h','l','c','v']); d = d[d.t < today].reset_index(drop=True); assert len(d) > 130; return d, name + ' ' + s
R = None
try: R = R or get('bitstamp', coin)
except Exception: pass
try: R = R or get('kraken', coin)
except Exception: pass
try: R = R or get('coinbase', coin)
except Exception: pass
try: R = R or get('kucoin', coin)
except Exception: pass
try: R = R or get('gateio', coin)
except Exception: pass
if R is None: requests.post(f"https://ntfy.sh/{TOPIC}", data=f"{coin}: not found on Bitstamp, Kraken, Coinbase, KuCoin or Gate.io. Check the spelling.".encode("utf-8"), headers={"Title": f"{coin} check: not found"}); raise SystemExit(0)
try: B = get('bitstamp', 'BTC')
except Exception: B = None
btc_up = True if B is None else bool(B[0].c.iloc[-1] > ta.trend.EMAIndicator(B[0].c,100).ema_indicator().iloc[-1])
d, src = R
c = d.c; ema = ta.trend.EMAIndicator(c,100).ema_indicator(); atr = ta.volatility.AverageTrueRange(d.h,d.l,c,14).average_true_range(); hh = d.h.rolling(20).max().shift(1); xl = d.l.rolling(10).min().shift(1)
px = float(c.iloc[-1]); e100 = float(ema.iloc[-1]); a = float(atr.iloc[-1]); stop = px - 3*a; risk = 3*a/px*100; hi20 = float(hh.iloc[-1]); x10 = float(xl.iloc[-1])
g = ((c > hh) & (c > ema)).values; idx = np.where(g)[0]; ago = int(len(c)-1-idx[-1]) if len(idx) else 999
up = px > e100; fresh = bool(g[-1] and not g[-2])
act = "NO TRADE" if not up else ("BUY SETUP" if (fresh and btc_up) else ("WAIT" if fresh else "NO FRESH ENTRY"))
watch = f"Watch for a close above {hi20:.4g} ({(hi20/px-1)*100:.1f}% away)." if hi20 > px else "Price is already above its 20-day high, so wait for a pullback and a new breakout."
why = {"NO TRADE": f"Below its 100-day average ({e100:.4g}), so it is in a downtrend. Shorts failed testing, so there is no short signal either.", "BUY SETUP": f"Fresh breakout above the 20-day high ({hi20:.4g}). Enter at the next day's open. Stop {stop:.4g} ({risk:.0f}% away). Exit if a daily close is below {x10:.4g}. For 1% risk, position about {100/risk:.0f}% of account.", "WAIT": "Fresh breakout, but BTC is below its 100-day average, so longs are paused.", "NO FRESH ENTRY": f"Uptrend, but no new breakout today (last one {ago} days ago). Late entries were not tested. {watch}"}[act]
body = f"{coin} on {src}: close {px:.4g}\nACTION: {act}\n{why}\nBTC is {'above' if btc_up else 'BELOW'} its 100-day average. PAPER mode, not financial advice."
requests.post(f"https://ntfy.sh/{TOPIC}", data=body.encode("utf-8"), headers={"Title": f"{coin} check: {act}"})
print(body)
