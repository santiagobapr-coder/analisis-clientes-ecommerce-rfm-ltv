"""Limpia Online Retail II y crea retail.sqlite (tablas: ventas, devoluciones)."""
import sqlite3, sys
import pandas as pd

SRC = sys.argv[1] if len(sys.argv) > 1 else "online_retail_II.xlsx"
hojas = pd.read_excel(SRC, sheet_name=None)
df = pd.concat(hojas.values(), ignore_index=True)
df.columns = ["factura", "codigo", "descripcion", "cantidad",
              "fecha", "precio", "cliente", "pais"]
n0 = len(df)

df["factura"] = df["factura"].astype(str)
df["codigo"] = df["codigo"].astype(str)
df = df.drop_duplicates()
n_dup = n0 - len(df)

# Solo productos reales (los códigos de producto empiezan con 5 dígitos)
df = df[df["codigo"].str.match(r"^\d{5}")]

# Devoluciones: facturas que empiezan por C
dev = df[df["factura"].str.startswith("C")].copy()
dev["ingreso"] = dev["cantidad"] * dev["precio"]

# Ventas: cantidad y precio positivos, sin cancelaciones
ven = df[~df["factura"].str.startswith("C") & (df["cantidad"] > 0) & (df["precio"] > 0)].copy()
ven["ingreso"] = (ven["cantidad"] * ven["precio"]).round(2)
ven["cliente"] = ven["cliente"].astype("Int64")
ven["fecha"] = ven["fecha"].dt.strftime("%Y-%m-%d %H:%M:%S")
dev["fecha"] = dev["fecha"].dt.strftime("%Y-%m-%d %H:%M:%S")
dev["cliente"] = dev["cliente"].astype("Int64")

con = sqlite3.connect("retail.sqlite")
ven.to_sql("ventas", con, if_exists="replace", index=False)
dev.to_sql("devoluciones", con, if_exists="replace", index=False)
con.execute("CREATE INDEX IF NOT EXISTS ix_v_cli ON ventas(cliente)")
con.commit()
print(f"filas originales: {n0:,} | duplicados: {n_dup:,}")
print(f"ventas: {len(ven):,} | con cliente: {ven['cliente'].notna().sum():,} | devoluciones: {len(dev):,}")
print(f"ingreso total: {ven['ingreso'].sum():,.2f}")
