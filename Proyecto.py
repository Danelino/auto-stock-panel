import streamlit as st  
import pandas as pd  
import matplotlib.pyplot as plt  
import seaborn as sns  
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
from datetime import datetime, timedelta


# Cargar datos
df = pd.read_csv("datos2020-2025.csv", sep=";", parse_dates=["Fecha_Venta"],
                 names=["Codigo_Boleta", "Codigo_Local", "Codigo_Repuesto", "Cantidad", "Fecha_Venta"])

# Cargar archivo de inventario
inventario = pd.read_csv("inventario.csv", sep=";",
                         names = ["Codigo_Local", "Codigo_Repuesto", "Cantidad_Stock"] )

# Cargar catálogo de marcas 
catalogo = pd.read_csv("Familia.csv", sep=";", names =["Letra", "Marca"])


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

# -----------------------------------------------------------
# 📦 MODELO DE PREDICCION DE DEMANDA MENSUAL POR LOCAL 
# -----------------------------------------------------------

st.subheader("📈 Predicción de Demanda para el Próximo Mes")

# 🗂️ Cargar ventas filtradas (asegúrate que df_filtrado ya existe)
df_filtrado_modelo = df_filtrado.copy()

# 🧹 Preprocesamiento
df_filtrado_modelo["Mes"] = df_filtrado_modelo["Fecha_Venta"].dt.to_period("M")

# Agrupar por Código_Local, Código_Repuesto y Mes
ventas_mensuales = df_filtrado_modelo.groupby([
    "Codigo_Local", "Codigo_Repuesto", "Mes"])["Cantidad"].sum().reset_index()

# 🔢 Codificar repuestos como números
ventas_mensuales["Codigo_Repuesto"] = ventas_mensuales["Codigo_Repuesto"].astype("category")
ventas_mensuales["Repuesto_ID"] = ventas_mensuales["Codigo_Repuesto"].cat.codes

# Convertir Mes a entero (YYYYMM)
ventas_mensuales["Mes_Num"] = ventas_mensuales["Mes"].astype(str).str.replace("-", "").astype(int)

# Filtrar por local seleccionado
ventas_local = ventas_mensuales[ventas_mensuales["Codigo_Local"] == local_seleccionado].copy()

# Variables predictoras y objetivo
X = ventas_local[["Repuesto_ID", "Mes_Num"]]
y = ventas_local["Cantidad"]

# Entrenar modelo
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
modelo = RandomForestRegressor(n_estimators=100, random_state=42)
modelo.fit(X_train, y_train)

# Evaluar modelo (opcional)
y_pred = modelo.predict(X_test)
mse = mean_squared_error(y_test, y_pred)
st.write(f"🔍 Error cuadrático medio del modelo: {mse:.2f}")

# 📅 Predecir próximo mes
ultimo_mes = ventas_local["Mes_Num"].max()
proximo_mes = (datetime.strptime(str(ultimo_mes), "%Y%m") + timedelta(days=32)).strftime("%Y%m")
proximo_mes = int(proximo_mes[:4] + proximo_mes[5:])

# Crear DataFrame con todos los repuestos para el próximo mes
repuestos_ids = ventas_local["Repuesto_ID"].unique()
X_pred = pd.DataFrame({
    "Repuesto_ID": repuestos_ids,
    "Mes_Num": proximo_mes
})

# Realizar predicción
predicciones = modelo.predict(X_pred)

# Mapear Repuesto_ID a Código_Repuesto
codigo_map = dict(zip(ventas_local["Repuesto_ID"], ventas_local["Codigo_Repuesto"]))
X_pred["Codigo_Repuesto"] = X_pred["Repuesto_ID"].map(codigo_map)
X_pred["Prediccion_Unidades"] = predicciones.astype(int)
X_pred["Mes"] = pd.to_datetime(str(proximo_mes), format="%Y%m").to_period("M")

# Mostrar resultados
st.write("🔮 Predicción de unidades a vender en el próximo mes:")
st.dataframe(X_pred[["Codigo_Repuesto", "Mes", "Prediccion_Unidades"]].sort_values("Prediccion_Unidades", ascending=False))

# Ejecutar Streamlit con:
# streamlit run nombre_del_archivo.py
