import os, time, ccxt, requests, pandas as pd, numpy as np, ta
TOPIC = os.environ["NTFY_TOPIC"]
ex = ccxt.bitstamp(); ex.load_markets()
WANT = ['BTC','ETH','XRP','LTC','ADA','SOL','DOGE','LINK','DOT','AVAX','UNI','ATOM','AAVE','ALGO','XLM','BCH','SHIB','NEAR','APT','ARB','OP','INJ','SUI','HBAR','FIL','MANA','SAND','AXS','GRT','CRV','COMP','SNX','ENJ','BAT','ZRX','MKR','YFI','SUSHI','1INCH','LRC','CHZ','ETC','EOS','XTZ','TRX']
syms = [w+'/USD' for w in WANT if w+'/USD' in ex.symbols]
since = ex.milliseconds() - 320*86400000
def get(s): b = ex.fetch_ohlcv(s,'1d',since=since,limit=400); time.sleep(0.4); return pd.DataFrame(b, columns=['t','o','h','l','c','v'])
D = {s: get(s) for s in syms}
today = int(time.time()//86400)*86400000
def sig(d): d = d[d.t < today].reset_index(drop=True); c = d.c; ema = ta.trend.EMAIndicator(c,100).ema_indicator(); atr = ta.volatility.AverageTrueRange(d.h,d.l,c,14).average_true_range(); g = (c > d.h.rolling(20).max().shift(1)) & (c > ema); xl = d.l.rolling(10).min().shift(1); return dict(fresh=bool(g.iloc[-1] and not g.iloc[-2]), px=float(c.iloc[-1]), ema=float(ema.iloc[-1]), stop=float(c.iloc[-1]-3*atr.iloc[-1]), risk=float(3*atr.iloc[-1]/c.iloc[-1]*100), xl=float(xl.iloc[-1]))
S = {s: sig(d) for s,d in D.items() if len(d)>150}
gate = S['BTC/USD']['px'] > S['BTC/USD']['ema']
hits = [f"LONG {s[:-4]}: close {v['px']:.4g}, stop {v['stop']:.4g} ({v['risk']:.0f}% away), exit if daily close < {v['xl']:.4g}" for s,v in S.items() if v['fresh']]
body = ("BTC above 100-day EMA. " if gate else "BTC below 100-day EMA: longs paused. ") + str(len(S)) + " coins scanned.\n" + ("\n".join(hits) if (hits and gate) else "No setups today.")
requests.post(f"https://ntfy.sh/{TOPIC}", data=body.encode("utf-8"), headers={"Title": "Daily trend scan (PAPER)"})
print(body)
import json
try: POS = json.load(open("positions.json"))
except Exception: POS = []
def chk(p): d = D[p["coin"]+"/USD"]; d = d[d.t < today].reset_index(drop=True); c = float(d.c.iloc[-1]); xl = float(d.l.rolling(10).min().shift(1).iloc[-1]); why = "STOP hit" if float(d.l.iloc[-1]) <= p["stop"] else ("closed below 10-day low" if c < xl else None); pl = (c/p["entry"]-1)*100; return (f"EXIT {p['coin']}: {why}. Close {c:.4g}, entry {p['entry']}, P&L {pl:+.1f}%" if why else f"HOLD {p['coin']}: close {c:.4g}, stop {p['stop']}, exit level {xl:.4g}, P&L {pl:+.1f}%")
if POS: requests.post(f"https://ntfy.sh/{TOPIC}", data="\n".join(chk(p) for p in POS).encode("utf-8"), headers={"Title": "Open paper trades"})
