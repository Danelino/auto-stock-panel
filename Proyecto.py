import streamlit as st  
import pandas as pd  
import matplotlib.pyplot as plt  
import seaborn as sns  

# Cargar datos
df = pd.read_csv("datos2020-2025.csv", sep=";", parse_dates=["Fecha_Venta"],
                 names=["Codigo_Boleta", "Codigo_Local", "Codigo_Repuesto", "Cantidad", "Fecha_Venta"])

# Cargar archivo de inventario
inventario = pd.read_csv("inventario.csv", sep=";",
                         names = ["Codigo_Local", "Codigo_Repuesto", "Cantidad_Stock"] )

# Cargar catálogo de marcas 
catalogo = pd.read_csv("familia.csv", sep=";", names =["Letra", "Marca"])


# colocar item -1 a 0

inventario["Cantidad_Stock"] = inventario["Cantidad_Stock"].apply(lambda x: x if x >= 0 else 0)


# Título del Dashboard
st.title("📊 Dashboard de Ventas - Auto Stock")

# Filtros interactivos
locales = df["Codigo_Local"].unique()
local_seleccionado = st.selectbox("Selecciona un Local", locales)

# Filtrar datos por local
df_filtrado = df[df["Codigo_Local"] == local_seleccionado]

# Filtro por fechas
fecha_min, fecha_max = df_filtrado["Fecha_Venta"].min(), df_filtrado["Fecha_Venta"].max()
fecha_inicio, fecha_fin = st.date_input("Rango de Fechas", [fecha_min, fecha_max])

df_filtrado = df_filtrado[(df_filtrado["Fecha_Venta"] >= pd.Timestamp(fecha_inicio)) & 
                          (df_filtrado["Fecha_Venta"] <= pd.Timestamp(fecha_fin))]

# Mostrar tabla de datos filtrados
st.write("📌 Datos Filtrados (Ventas):")
st.dataframe(df_filtrado)

# 📈 Top 50 productos más vendidos
top_50_productos = df_filtrado.groupby("Codigo_Repuesto")["Cantidad"].sum().sort_values(ascending=False).head(50)

st.subheader("🔥 Top 50 Productos Más Vendidos")
fig, ax = plt.subplots(figsize=(12, 6))
sns.barplot(x=top_50_productos.index, y=top_50_productos.values, ax=ax, palette="Blues_r")
plt.xticks(rotation=90)
plt.xlabel("Código de Repuesto")
plt.ylabel("Cantidad Vendida")
st.pyplot(fig)

# Extraer letra de Código_Repuesto
df_filtrado["Marca_Letra"] = df_filtrado["Codigo_Repuesto"].astype(str).str[0]

# Unir con catálogo para obtener el nombre de la marca
df_filtrado = df_filtrado.merge(catalogo, left_on="Marca_Letra", right_on="Letra", how="left")

# Agrupar por Local y Marca
ventas_marca_local = df_filtrado.groupby(["Codigo_Local", "Marca"])["Cantidad"].sum().reset_index()
ventas_marca_local = ventas_marca_local.sort_values(["Codigo_Local", "Cantidad"], ascending=[True, False])


# ----------------------------
# 🔍 Análisis de Inventario y Rotación
# ----------------------------

# Agrupar ventas por producto y local (total vendido)
ventas_agrupadas = df_filtrado.groupby(["Codigo_Local", "Codigo_Repuesto"])["Cantidad"].sum().reset_index()
ventas_agrupadas.rename(columns={"Cantidad": "Cantidad_Vendida"}, inplace=True)

# Unir con inventario para el local seleccionado
inventario_local = inventario[inventario["Codigo_Local"] == local_seleccionado]
df_inventario = pd.merge(inventario_local, ventas_agrupadas, on=["Codigo_Local", "Codigo_Repuesto"], how="left")
df_inventario["Cantidad_Vendida"] = df_inventario["Cantidad_Vendida"].fillna(0)

# Calcular rotación: ventas / stock (agregamos +1 para evitar división por cero)
df_inventario["Rotacion"] = df_inventario["Cantidad_Vendida"] / (df_inventario["Cantidad_Stock"] + 1)

# Eliminar productos sin stock y sin ventas
df_inventario = df_inventario[~((df_inventario["Cantidad_Stock"] == 0) & (df_inventario["Cantidad_Vendida"] == 0))]


# Clasificación según cuartiles
umbral_alto = df_inventario["Rotacion"].quantile(0.75)
umbral_bajo = df_inventario["Rotacion"].quantile(0.25)

def clasificar_rotacion(row):
    if row["Cantidad_Vendida"] == 0 and row["Cantidad_Stock"] > 0:
        return "⚠️ Revisar (stock sin ventas)"
    elif row["Rotacion"] >= umbral_alto:
        return "✅ Mantener en stock"
    elif row["Rotacion"] <= umbral_bajo:
        return "⚠️ Revisar"
  

df_inventario["Recomendacion"] = df_inventario.apply(clasificar_rotacion, axis=1)


# ----------------------------
# 🛒 Recomendación de compra por falta de stock
# ----------------------------

# Filtrar ventas con cantidad negativa (ventas sin stock)
ventas_sin_stock = df_filtrado[df_filtrado["Cantidad"] < 0]

# Agrupar por repuesto
recomendaciones_compra = ventas_sin_stock.groupby("Codigo_Repuesto")["Cantidad"].count().reset_index()
recomendaciones_compra.rename(columns={"Cantidad": "Intentos_Fallidos"}, inplace=True)

# Añadir columna de recomendación
recomendaciones_compra["Recomendacion"] = "🔄 Evaluar su compra"

# ----------------------------
# 📋 Mostrar recomendaciones
# ----------------------------

st.subheader("📦 Recomendaciones de Stock ")


# Selector de cantidad de filas a mostrar
cantidad_a_mostrar = st.selectbox(
    "¿Cuántos productos quieres visualizar por sección?",
    options=[10, 20, 50, 100, len(df_inventario)],
    index=0,
    format_func=lambda x: "Todos" if x == len(df_inventario) else x
)

# Mostrar Productos con buena rotación
st.write("✅ Productos con buena rotación (conviene mantener):")
st.dataframe(df_inventario[df_inventario["Recomendacion"] == "✅ Mantener en stock"]
             .sort_values("Rotacion", ascending=False).head(cantidad_a_mostrar))

# Mostrar si hay datos
st.write("🛒 Repuestos Recomendados para Comprar (por ventas sin stock):")
if not recomendaciones_compra.empty:    
    st.dataframe(recomendaciones_compra.sort_values("Intentos_Fallidos", ascending=False).head(cantidad_a_mostrar))
else:
    st.write("✅ No se encontraron intentos de venta fallida por falta de stock en el período seleccionado.")

# Mostrar roductos con stock sin ventas
st.write("⚠️ Productos con stock sin ventas:")
st.dataframe(df_inventario[df_inventario["Recomendacion"] == "⚠️ Revisar (stock sin ventas)"]
             .sort_values("Cantidad_Stock", ascending=False).head(cantidad_a_mostrar))


# 📊 Ventas por Marca y Local
st.subheader("🏷️ Ventas Totales por Marca y Local")
st.dataframe(ventas_marca_local)

# Gráfico interactivo por local
st.subheader("📍 Gráfico de Marcas Más Vendidas por Local")


df_local_marca = ventas_marca_local[ventas_marca_local["Codigo_Local"] == local_seleccionado]

fig, ax = plt.subplots(figsize=(20, 5))
sns.barplot(data=df_local_marca, x="Marca", y="Cantidad", ax=ax, palette="viridis")
plt.title(f"🔝 Marcas más vendidas - Local ")
plt.xticks(rotation=45)
plt.xlabel("Marca")
plt.ylabel("Cantidad Vendida")
st.pyplot(fig)


# Ejecutar Streamlit con:
# streamlit run nombre_del_archivo.py
