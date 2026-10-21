"""Corre queries.sql sobre retail.sqlite, exporta CSV a resultados/ y genera gráficos en graficos/."""
import os, re, sqlite3
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

os.makedirs("resultados", exist_ok=True)
os.makedirs("graficos", exist_ok=True)
con = sqlite3.connect("retail.sqlite")
sql = open("queries.sql", encoding="utf-8").read()
partes = re.split(r"^-- name:\s*(\w+)\s*$", sql, flags=re.M)
res = {}
for nombre, cuerpo in zip(partes[1::2], partes[2::2]):
    res[nombre] = pd.read_sql_query(cuerpo.strip().rstrip(";"), con)
    res[nombre].to_csv(f"resultados/{nombre}.csv", index=False)
    print(f"{nombre}: {len(res[nombre])} filas")

AZUL, GRIS = "#2A6F97", "#5B6B7B"
plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False, "font.size": 10})

# 1. Ingresos mensuales
m = res["ingresos_mensuales"]
fig, ax = plt.subplots(figsize=(9, 3.6))
ax.plot(m["mes"], m["ingresos"] / 1e3, color=AZUL, lw=2)
ax.set_title("Ingresos mensuales (miles de £)", loc="left", color=GRIS)
ax.set_xticks(range(0, len(m), 3)); ax.set_xticklabels(m["mes"][::3], rotation=45, ha="right")
fig.tight_layout(); fig.savefig("graficos/ingresos_mensuales.png", dpi=130); plt.close(fig)

# 2. Ingresos por segmento RFM
r = res["rfm_clientes"]
seg = r.groupby("segmento").agg(clientes=("cliente", "count"), ingresos=("monetario", "sum"))
seg["pct_clientes"] = 100 * seg.clientes / seg.clientes.sum()
seg["pct_ingresos"] = 100 * seg.ingresos / seg.ingresos.sum()
seg = seg.sort_values("pct_ingresos")
seg.round(1).to_csv("resultados/resumen_segmentos.csv")
fig, ax = plt.subplots(figsize=(9, 3.6))
y = range(len(seg))
ax.barh([i + 0.2 for i in y], seg["pct_ingresos"], height=0.4, color=AZUL, label="% de ingresos")
ax.barh([i - 0.2 for i in y], seg["pct_clientes"], height=0.4, color="#A9C7DB", label="% de clientes")
ax.set_yticks(list(y)); ax.set_yticklabels(seg.index); ax.legend(frameon=False)
ax.set_title("Clientes vs ingresos por segmento RFM", loc="left", color=GRIS)
fig.tight_layout(); fig.savefig("graficos/segmentos_rfm.png", dpi=130); plt.close(fig)

# 3. Retención por cohorte (mapa de calor, cohortes con 12+ meses de historia)
co = res["cohortes_retencion"]
piv = co.pivot(index="cohorte", columns="mes_n", values="retencion_pct")
piv = piv[piv.index <= "2010-12"].loc[:, 0:12]
fig, ax = plt.subplots(figsize=(9, 5))
im = ax.imshow(piv.values, cmap="Blues", vmin=0, vmax=60, aspect="auto")
ax.set_xticks(range(piv.shape[1])); ax.set_xticklabels(piv.columns)
ax.set_yticks(range(len(piv))); ax.set_yticklabels(piv.index)
ax.set_xlabel("Meses desde la primera compra")
ax.set_title("Retención de clientes por cohorte (%)", loc="left", color=GRIS)
for i in range(piv.shape[0]):
    for j in range(piv.shape[1]):
        v = piv.values[i, j]
        if pd.notna(v):
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=7, color="white" if v > 35 else "#1F3A52")
fig.tight_layout(); fig.savefig("graficos/retencion_cohortes.png", dpi=130); plt.close(fig)

# 4. LTV acumulado por cliente (cohortes agrupadas por trimestre de adquisición)
ing = res["ingresos_por_cohorte"].merge(co[["cohorte", "tamano_cohorte"]].drop_duplicates(), on="cohorte")
ing["trimestre"] = pd.PeriodIndex(ing["cohorte"], freq="M").asfreq("Q").astype(str)
t = ing.groupby(["trimestre", "mes_n"]).agg(ing=("ingresos", "sum")).reset_index()
tam = ing.drop_duplicates("cohorte").groupby("trimestre")["tamano_cohorte"].sum()
t["ltv"] = t.apply(lambda f: f["ing"] / tam[f["trimestre"]], axis=1)
fig, ax = plt.subplots(figsize=(9, 3.8))
ltv_tab = {}
for q in ["2010Q1", "2010Q2", "2010Q3", "2010Q4"]:
    d = t[(t.trimestre == q) & (t.mes_n <= 12)].sort_values("mes_n")
    d = d.assign(acum=d["ltv"].cumsum())
    ax.plot(d["mes_n"], d["acum"], lw=2, label=q)
    ltv_tab[q] = round(d["acum"].iloc[-1], 0)
ax.set_xlabel("Meses desde la adquisición"); ax.set_title("LTV acumulado por cliente en £ (ingresos, no margen)", loc="left", color=GRIS)
ax.legend(frameon=False, title="Cohorte")
fig.tight_layout(); fig.savefig("graficos/ltv_cohortes.png", dpi=130); plt.close(fig)
pd.Series(ltv_tab, name="ltv_12m_gbp").to_csv("resultados/ltv_12m.csv")
print("LTV a 12 meses:", ltv_tab)
print(seg.round(1))
