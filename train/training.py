!pip install -q xgboost==3.3.0 >/dev/null 2>&1
import numpy as np, pandas as pd, matplotlib.pyplot as plt, warnings, pickle, json
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from scipy import stats
import xgboost as xgb, time
warnings.filterwarnings('ignore'); np.random.seed(42)
print("xgboost", xgb.__version__)

from google.colab import files
up = files.upload()
df = pd.read_excel(list(up.keys())[0])
df['tanggal'] = pd.to_datetime(df['tanggal'])
print("Ukuran awal:", df.shape)

print("\n=== CEK VARIABEL STATIS PER TAHUN ===")
print(df.groupby(['stasiun', df['tanggal'].dt.year])[['kepadatan_penduduk_jiwa_km2','luas_rth_km2']].first())

df = df.drop(columns=[c for c in ['max','parameter_kritis','kategori'] if c in df.columns])
df = df.sort_values(['stasiun','tanggal']).reset_index(drop=True)

df['pm25_asli'] = df['pm25'].notna()
pol = ['pm10','pm25','so2','co','o3','no2']
df[pol] = df.groupby('stasiun')[pol].transform(lambda s: s.ffill(limit=7))

g = df.groupby('stasiun')
for lg in [1,2,3]:
    df[f'pm25_lag{lg}'] = g['pm25'].shift(lg)
df['pm25_roll3'] = g['pm25'].transform(lambda s: s.shift(1).rolling(3).mean())
df['bulan'] = df['tanggal'].dt.month
df['hari']  = df['tanggal'].dt.dayofweek

g = df.groupby('stasiun')
for h in [1,2,3,4,5,6,7]:
    df[f'target_h{h}']      = g['pm25'].shift(-h)
    df[f'target_h{h}_asli'] = g['pm25_asli'].shift(-h)

FITUR = ['kepadatan_penduduk_jiwa_km2','luas_rth_km2',
         'suhu_c','kelembapan_pct','curah_hujan_mm','tutupan_awan_pct',
         'kecepatan_angin_kmh','tekanan_hpa','arah_angin_deg',
         'pm10','pm25','so2','co','o3','no2',
         'pm25_lag1','pm25_lag2','pm25_lag3','pm25_roll3','bulan','hari']
NOVELTY = ['kepadatan_penduduk_jiwa_km2','luas_rth_km2']

df = df.dropna(subset=['pm25_lag1','pm25_lag2','pm25_lag3','pm25_roll3',
                       'target_h1','target_h2','target_h3',
                       'target_h4','target_h5','target_h6','target_h7']).reset_index(drop=True)
for h in [1,2,3,4,5,6,7]:
    df[f'target_h{h}_asli'] = df[f'target_h{h}_asli'].fillna(False).astype(bool)
print("Baris siap model:", len(df), "(harus 3225) | jumlah fitur:", len(FITUR))

tu = np.sort(df['tanggal'].unique()); n = len(tu)
batas_latih, batas_val = tu[int(n*0.70)], tu[int(n*0.85)]
m_tr = df['tanggal'] <  batas_latih
m_va = (df['tanggal'] >= batas_latih) & (df['tanggal'] < batas_val)
m_te = df['tanggal'] >= batas_val
print(f"Train {m_tr.sum()} | Val {m_va.sum()} | Test {m_te.sum()}")

def metrik(y_true, y_pred, asli):
    yt = np.asarray(y_true, float)[asli]; yp = np.asarray(y_pred, float)[asli]
    v = yt != 0
    return dict(MAE=mean_absolute_error(yt,yp),
                RMSE=np.sqrt(mean_squared_error(yt,yp)),
                MAPE=np.mean(np.abs((yt[v]-yp[v])/yt[v]))*100,
                R2=r2_score(yt,yp))

def latih(cols, h, params):
    scl = StandardScaler().fit(df.loc[m_tr, cols])
    Xtr, Xva, Xte = scl.transform(df.loc[m_tr,cols]), scl.transform(df.loc[m_va,cols]), scl.transform(df.loc[m_te,cols])
    ytr, yva, yte = df.loc[m_tr,f'target_h{h}'], df.loc[m_va,f'target_h{h}'], df.loc[m_te,f'target_h{h}']
    m = xgb.XGBRegressor(random_state=42, n_jobs=-1, early_stopping_rounds=50, eval_metric='rmse', **params)
    m.fit(Xtr, ytr, eval_set=[(Xva,yva)], verbose=False)
    a = df.loc[m_te,f'target_h{h}_asli'].values.astype(bool)
    pred = m.predict(Xte)
    return m, scl, metrik(yte, pred, a), pred

DEF = dict(n_estimators=600, max_depth=6, learning_rate=0.3,
           subsample=1.0, colsample_bytree=1.0,
           min_child_weight=1, reg_alpha=0.0, reg_lambda=1.0)
print("\n=== BASELINE per horizon ===")
base = {}
t0 = time.perf_counter()
for h in [1,2,3,4,5,6,7]:
    _,_,r,_ = latih(FITUR, h, DEF); base[h]=r
    print(f"t+{h}: MAE={r['MAE']:.3f} RMSE={r['RMSE']:.3f} MAPE={r['MAPE']:.2f}% R2={r['R2']:.3f}")

waktu_bawaan = time.perf_counter() - t0
print(f"Waktu latih 7 model bawaan: {waktu_bawaan:.1f} detik")

BB = np.array([3, 0.01, 0.50, 0.50, 1, 0.00, 0.50])
BA = np.array([10, 0.30, 1.00, 1.00, 10, 2.00, 5.00])
def dekode(p):
    return dict(max_depth=int(round(p[0])), learning_rate=float(p[1]),
                subsample=float(p[2]), colsample_bytree=float(p[3]),
                min_child_weight=int(round(p[4])), reg_alpha=float(p[5]),
                reg_lambda=float(p[6]), n_estimators=600)

scl1 = StandardScaler().fit(df.loc[m_tr, FITUR])
Xtr1, Xva1 = scl1.transform(df.loc[m_tr,FITUR]), scl1.transform(df.loc[m_va,FITUR])
ytr1, yva1 = df.loc[m_tr,'target_h1'], df.loc[m_va,'target_h1']
cache = {}
def fitness(p):
    pr = dekode(p); key = tuple(round(v,4) if isinstance(v,float) else v for v in pr.values())
    if key in cache: return cache[key]
    m = xgb.XGBRegressor(random_state=42, n_jobs=-1, early_stopping_rounds=50, eval_metric='rmse', **pr)
    m.fit(Xtr1, ytr1, eval_set=[(Xva1,yva1)], verbose=False)
    r = np.sqrt(mean_squared_error(yva1, m.predict(Xva1))); cache[key]=r; return r

t0 = time.perf_counter()
rng = np.random.default_rng(42)
N_PARTIKEL, N_ITERASI = 20, 40
w_awal, w_akhir, c1, c2 = 0.9, 0.4, 1.5, 1.5
rentang = BA - BB
pos = BB + rng.random((N_PARTIKEL,7))*rentang
vmax = 0.5*rentang
vel = rng.uniform(-1,1,(N_PARTIKEL,7))*vmax
skor = np.array([fitness(p) for p in pos])
pbest, pbs = pos.copy(), skor.copy()
gi = int(np.argmin(pbs)); gbest = pbest[gi].copy(); gbs = float(pbs[gi])
riwayat = [gbs]
print(f"\n=== PSO ===\nIter  0 | gbest RMSE(val) = {gbs:.4f}")
for it in range(1, N_ITERASI+1):
    w = w_awal - (w_awal - w_akhir) * it / N_ITERASI
    for i in range(N_PARTIKEL):
        r1, r2 = rng.random(7), rng.random(7)
        vel[i] = np.clip(w*vel[i] + c1*r1*(pbest[i]-pos[i]) + c2*r2*(gbest-pos[i]), -vmax, vmax)
        pos[i] = np.clip(pos[i]+vel[i], BB, BA)
        s = fitness(pos[i])
        if s < pbs[i]:
            pbs[i], pbest[i] = s, pos[i].copy()
            if s < gbs: gbs, gbest = float(s), pos[i].copy()
    riwayat.append(gbs)
    print(f"Iter {it:2d} | w={w:.3f} | gbest RMSE(val) = {gbs:.4f}")
BEST = dekode(gbest)
waktu_pso = time.perf_counter() - t0
n_unik_pso = len(cache)
print(f"Waktu pencarian PSO: {waktu_pso:.1f} detik | kombinasi unik: {n_unik_pso}")
print("\nHyperparameter terbaik:", {k:(round(v,4) if isinstance(v,float) else v) for k,v in BEST.items()})

plt.figure(figsize=(7,4))
plt.plot(range(len(riwayat)), riwayat, marker='o')
plt.xlabel('Iterasi'); plt.ylabel('RMSE validasi (gbest)')
plt.title('Kurva Konvergensi PSO'); plt.grid(alpha=.3); plt.tight_layout(); plt.show()

print("\n=== XGBoost + PSO per horizon ===")
pso = {}
t0 = time.perf_counter()
for h in [1,2,3,4,5,6,7]:
    m, scl, r, _ = latih(FITUR, h, BEST); pso[h]=r
    with open(f'model_pm25_h{h}.pkl','wb') as f:
        pickle.dump({'model':m, 'scaler':scl, 'fitur':FITUR, 'horizon':h}, f)
    print(f"t+{h}: MAE={r['MAE']:.3f} RMSE={r['RMSE']:.3f} MAPE={r['MAPE']:.2f}% R2={r['R2']:.3f}  -> model_pm25_h{h}.pkl")

waktu_final_pso = time.perf_counter() - t0
print(f"Waktu latih 7 model final PSO: {waktu_final_pso:.1f} detik")

print("\n"+"="*64)
print(f"{'Horizon':9s}{'Model':10s}{'MAE':>9s}{'RMSE':>9s}{'MAPE':>9s}{'R2':>9s}")
print("="*64)
for h in [1,2,3,4,5,6,7]:
    for nm, r in [('Baseline',base[h]),('XGB+PSO',pso[h])]:
        print(f"{'t+'+str(h):9s}{nm:10s}{r['MAE']:9.3f}{r['RMSE']:9.3f}{r['MAPE']:8.2f}%{r['R2']:9.3f}")

df = pd.concat([df, pd.get_dummies(df['stasiun'], prefix='st').astype(int)], axis=1)
ST = [c for c in df.columns if c.startswith('st_')]
DASAR = [c for c in FITUR if c not in NOVELTY]
def dm_test(y, p1, p2, h=1):
    e1, e2 = y-p1, y-p2; d = e1**2 - e2**2; nT=len(d); g0=np.var(d,ddof=0)
    gm=[np.cov(d[k:],d[:-k])[0,1] for k in range(1,h)] if h>1 else []
    vd=(g0+2*sum(gm))/nT
    if vd<=0: return np.nan, np.nan
    s=np.mean(d)/np.sqrt(vd); return s, 2*(1-stats.t.cdf(abs(s),nT-1))

print("\n=== S1/S2/S3 + Diebold-Mariano (S1 vs S3) ===")
skenario_json, baris_sk = {}, []
for h in [1,2,3,4,5,6,7]:
    _,_,r1,p1 = latih(DASAR,     h, BEST)
    _,_,r2,_  = latih(DASAR+ST,  h, BEST)
    _,_,r3,p3 = latih(FITUR, h, BEST)
    a = df.loc[m_te,f'target_h{h}_asli'].values.astype(bool)
    yt = df.loc[m_te,f'target_h{h}'].values[a]
    s, pv = dm_test(yt, p1[a], p3[a], h)
    print(f"t+{h}: S1={r1['RMSE']:.3f} S2={r2['RMSE']:.3f} S3={r3['RMSE']:.3f} | DM={s:.3f} p={pv:.4f}")
    for nama, r in [('S1', r1), ('S2', r2), ('S3', r3)]:
        baris_sk.append({'Horizon': f't+{h}', 'Skenario': nama, **{k: round(float(v), 3) for k, v in r.items()}})
    skenario_json[str(h)] = {'S1': round(r1['RMSE'], 3), 'S2': round(r2['RMSE'], 3), 'S3': round(r3['RMSE'], 3),
                             'DM': round(float(s), 3), 'p': round(float(pv), 4),
                             'lengkap': {nm: {k: round(float(v), 3) for k, v in r.items()}
                                         for nm, r in [('S1', r1), ('S2', r2), ('S3', r3)]}}

tabel_sk_lengkap = pd.DataFrame(baris_sk)
print(tabel_sk_lengkap.to_string(index=False))
print(tabel_sk_lengkap.groupby('Skenario')[['MAE','RMSE','MAPE','R2']].mean().round(3))
with open('hasil_skenario.json', 'w') as f:
    json.dump({'sumber': 'Output Colab sel 10, hyperparameter BEST PSO',
               'metrik': 'RMSE data uji (hanya nilai PM2.5 asli)', 'skenario': skenario_json}, f, indent=2)
tabel_sk_lengkap.to_excel('tabel_skenario_lengkap.xlsx', index=False)

m1, scl1b, _, _ = latih(FITUR, 1, BEST)
imp = pd.Series(m1.feature_importances_, index=FITUR).sort_values()
plt.figure(figsize=(8,7)); imp.plot(kind='barh')
plt.title('Feature Importance (XGBoost + PSO, t+1)'); plt.xlabel('Importance')
plt.tight_layout(); plt.show()
print("\nPeringkat novelty (t+1):")
imp_desc = imp.sort_values(ascending=False)
for f in NOVELTY:
    print(f"  {f}: peringkat {list(imp_desc.index).index(f)+1} dari {len(FITUR)}")

print("\n=== BASELINE PERSISTENCE (naif) vs XGB+PSO ===")
pm_te_hari_ini = df.loc[m_te, 'pm25'].values
persist = {}
for h in [1,2,3,4,5,6,7]:
    a  = df.loc[m_te, f'target_h{h}_asli'].values.astype(bool)
    yt = df.loc[m_te, f'target_h{h}'].values
    r  = metrik(yt, pm_te_hari_ini, a)
    persist[h] = r
    menang = "menang" if pso[h]['RMSE'] < r['RMSE'] else "KALAH"
    print(f"t+{h}: Persistence RMSE={r['RMSE']:.3f} R2={r['R2']:.3f}  |  "
          f"XGB+PSO RMSE={pso[h]['RMSE']:.3f} R2={pso[h]['R2']:.3f}  ({menang})")

SEEDS = [42, 1, 7, 123, 2024]
def latih_seed(cols, h, params, seed):
    p = dict(params); p['random_state'] = seed
    scl = StandardScaler().fit(df.loc[m_tr, cols])
    Xtr, Xva, Xte = scl.transform(df.loc[m_tr,cols]), scl.transform(df.loc[m_va,cols]), scl.transform(df.loc[m_te,cols])
    ytr, yva, yte = df.loc[m_tr,f'target_h{h}'], df.loc[m_va,f'target_h{h}'], df.loc[m_te,f'target_h{h}']
    m = xgb.XGBRegressor(n_jobs=-1, early_stopping_rounds=50, eval_metric='rmse', **p)
    m.fit(Xtr, ytr, eval_set=[(Xva,yva)], verbose=False)
    a = df.loc[m_te,f'target_h{h}_asli'].values.astype(bool)
    return metrik(yte, m.predict(Xte), a)

print(f"\n=== KESTABILAN MULTI-SEED (XGB+PSO, {len(SEEDS)} seed) ===")
print(f"{'Horizon':9s}{'RMSE (mean±std)':>20s}{'R2 (mean±std)':>20s}")
for h in [1,2,3,4,5,6,7]:
    res   = [latih_seed(FITUR, h, BEST, s) for s in SEEDS]
    rmses = [x['RMSE'] for x in res]; r2s = [x['R2'] for x in res]
    print(f"{'t+'+str(h):9s}{np.mean(rmses):8.3f} ± {np.std(rmses):.3f}   {np.mean(r2s):8.3f} ± {np.std(r2s):.3f}")

N_EVAL_RS = N_PARTIKEL * (N_ITERASI + 1)
cache.clear()
t0 = time.perf_counter()
rng_rs = np.random.default_rng(42)

best_rs, best_rs_skor = None, np.inf
riwayat_rs = []
print(f"\n=== RANDOM SEARCH ({N_EVAL_RS} evaluasi) ===")
for i in range(N_EVAL_RS):
    p = BB + rng_rs.random(7) * rentang
    s = fitness(p)
    if s < best_rs_skor:
        best_rs_skor, best_rs = s, p.copy()
    if (i + 1) % N_PARTIKEL == 0:
        riwayat_rs.append(best_rs_skor)
BEST_RS = dekode(best_rs)
waktu_rs = time.perf_counter() - t0
n_unik_rs = len(cache)
print(f"Waktu pencarian Random Search: {waktu_rs:.1f} detik | kombinasi unik: {n_unik_rs}")
print(f"RMSE(val) terbaik RS = {best_rs_skor:.4f} | PSO = {gbs:.4f}")
print("Hyperparameter RS:", {k:(round(v,4) if isinstance(v,float) else v) for k,v in BEST_RS.items()})

plt.figure(figsize=(7,4))
plt.plot(range(len(riwayat)), riwayat, marker='o', label='PSO')
plt.plot(range(len(riwayat_rs)), riwayat_rs, marker='s', label='Random Search')
plt.xlabel(f'Iterasi (1 iterasi = {N_PARTIKEL} evaluasi)'); plt.ylabel('RMSE validasi terbaik')
plt.title('Konvergensi PSO vs Random Search'); plt.legend(); plt.grid(alpha=.3)
plt.tight_layout(); plt.show()

print("\n" + "="*72)
print(f"{'Horizon':9s}{'Model':10s}{'MAE':>9s}{'RMSE':>9s}{'MAPE':>9s}{'R2':>9s}")
print("="*72)
rs = {}
waktu_final_rs = 0.0
for h in [1,2,3,4,5,6,7]:
    t1 = time.perf_counter()
    _,_,r_rs,p_rs  = latih(FITUR, h, BEST_RS); rs[h] = r_rs
    waktu_final_rs += time.perf_counter() - t1
    _,_,_,  p_pso  = latih(FITUR, h, BEST)
    for nm, r in [('Default',base[h]), ('RandomS',r_rs), ('PSO',pso[h])]:
        print(f"{'t+'+str(h):9s}{nm:10s}{r['MAE']:9.3f}{r['RMSE']:9.3f}{r['MAPE']:8.2f}%{r['R2']:9.3f}")
    a  = df.loc[m_te, f'target_h{h}_asli'].values.astype(bool)
    yt = df.loc[m_te, f'target_h{h}'].values[a]
    s, pv = dm_test(yt, p_rs[a], p_pso[a], h)
    arah = 'PSO lebih baik' if s > 0 else 'RS lebih baik'
    sig  = 'SIGNIFIKAN' if (not np.isnan(pv) and pv < 0.05) else 'tidak signifikan'
    print(f"{'':9s}DM RS vs PSO = {s:.3f}, p = {pv:.4f} ({arah}, {sig})")
    print("-"*72)

def periode(t):
    if t < pd.Timestamp('2025-09-01'): return 'Agustus (29 Jul–31 Agu)'
    if t < pd.Timestamp('2025-10-01'): return 'September'
    return 'Okt–Nov (1 Okt–8 Nov)'

baris = []
for h in [1,2,3,4,5,6,7]:
    _, _, _, pred = latih(FITUR, h, BEST)
    uji = df.loc[m_te, ['tanggal', f'target_h{h}', f'target_h{h}_asli']].copy()
    uji['pred'] = pred
    uji = uji[uji[f'target_h{h}_asli']]
    uji['periode'] = (uji['tanggal'] + pd.Timedelta(days=h)).map(periode)
    for p, g in uji.groupby('periode'):
        r = metrik(g[f'target_h{h}'], g['pred'], np.ones(len(g), bool))
        baris.append({'Horizon': f't+{h}', 'Periode': p, 'n': len(g),
                      **{k: round(v, 3) for k, v in r.items()}})

tabel_periode = pd.DataFrame(baris)
print(tabel_periode.to_string(index=False))
tabel_periode.to_excel('tabel_metrik_periode.xlsx', index=False)
files.download('tabel_metrik_periode.xlsx')

waktu = pd.DataFrame([
    {'Metode': 'XGBoost bawaan', 'Pencarian (detik)': 0.0, 'Latih 7 model (detik)': waktu_bawaan, 'Kombinasi unik': 1},
    {'Metode': 'Random Search', 'Pencarian (detik)': waktu_rs, 'Latih 7 model (detik)': waktu_final_rs, 'Kombinasi unik': n_unik_rs},
    {'Metode': 'PSO', 'Pencarian (detik)': waktu_pso, 'Latih 7 model (detik)': waktu_final_pso, 'Kombinasi unik': n_unik_pso},
])
waktu['Total (menit)'] = (waktu['Pencarian (detik)'] + waktu['Latih 7 model (detik)']) / 60
print(waktu.round(2).to_string(index=False))
waktu.round(2).to_excel('tabel_waktu_komputasi.xlsx', index=False)
for f in ['hasil_skenario.json', 'tabel_skenario_lengkap.xlsx', 'tabel_waktu_komputasi.xlsx']:
    files.download(f)

for nama, m in [('Latih', m_tr), ('Validasi', m_va), ('Uji', m_te)]:
    g = df[m & df['pm25_asli']]
    ak = np.mean([x.sort_values('tanggal')['pm25'].where(x['pm25_asli']).autocorr(1)
                  for _, x in df[m].groupby('stasiun')])
    print(f"{nama}: n={m.sum()} rata-rata={g['pm25'].mean():.2f} SD={g['pm25'].std(ddof=0):.2f} "
          f">100={(g['pm25']>100).mean()*100:.1f}% autokorelasi={ak:.3f}")

_, _, _, pred = latih(FITUR, 1, BEST)
a  = df.loc[m_te, 'target_h1_asli'].values.astype(bool)
y  = df.loc[m_te, 'target_h1'].values[a]; yh = pred[a]; e = y - yh
rmse = np.sqrt(np.mean(e**2))
print(f"SD aktual={y.std():.2f} | SD prediksi={yh.std():.2f} | RMSE={rmse:.3f} | R2={1-(rmse/y.std())**2:.3f}")
se = np.sort(e**2)[::-1]
print(f"10% error terbesar menyumbang {se[:len(se)//10].sum()/se.sum()*100:.1f}% total error kuadrat")
besar = np.abs(e) > 2*rmse
print(f"data dengan error > 2xRMSE: {besar.sum()} | R2 tanpa data tersebut: {r2_score(y[~besar], yh[~besar]):.3f}")
lonjak = y > 100
print(f"data aktual >100: {lonjak.sum()} | rata aktual {y[lonjak].mean():.1f} | rata prediksi {yh[lonjak].mean():.1f}")

with open('hasil_evaluasi.json','w') as f:
    json.dump({'default':base, 'random_search':rs, 'pso':pso, 'persistence':persist,
               'best_pso':BEST, 'best_rs':BEST_RS}, f, indent=2, default=float)

from google.colab import files
for h in [1,2,3,4,5,6,7]: files.download(f'model_pm25_h{h}.pkl')
files.download('hasil_evaluasi.json')
print("\nSELESAI. Tersimpan: model_pm25_h1.pkl ... model_pm25_h7.pkl + hasil_evaluasi.json")
