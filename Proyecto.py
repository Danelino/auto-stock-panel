import streamlit as st  
import pandas as pd  
import matplotlib.pyplot as plt  
import seaborn as sns  
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from datetime import datetime, timedelta


# ----------------------------
# Codigo para autenticacion desde csv
# ----------------------------

def cargar_usuarios():
    try:
        return pd.read_csv("usuarios.csv")
    except FileNotFoundError:
        st.error("Archivo de usuarios no encontrado.")
        return pd.DataFrame(columns=["usuario", "contraseña"])

def login():
    st.title("🔐 Inicio de Sesión")
    usuarios_df = cargar_usuarios()

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        usuario = st.text_input("Usuario")
        contraseña = st.text_input("Contraseña", type="password")

        if st.button("Iniciar sesión"):
            if not usuarios_df.empty:
                validacion = usuarios_df[
                    (usuarios_df["usuario"] == usuario) &
                    (usuarios_df["contraseña"] == contraseña)
                ]

                if not validacion.empty:
                    st.session_state.logged_in = True
                    st.session_state.usuario = usuario
                    st.success(f"Bienvenido, {usuario}")
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos")
    else:
        st.success(f"Sesión iniciada como: {st.session_state.usuario}")
        return True

    return False

# ----------------------------
# Uso en tu app principal
# ----------------------------

if login():
    st.sidebar.write(f"👤 Usuario: {st.session_state.usuario}")
    
    
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
    st.title("📊 Panel de Ventas - Auto Stock")

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
    index=0
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



    st.subheader("📈 Predicción de Demanda para el Próximo Mes (Modelo Optimizado)")

    # Crear copia de datos filtrados
    df_filtrado_modelo = df_filtrado.copy()
    df_filtrado_modelo["Mes"] = df_filtrado_modelo["Fecha_Venta"].dt.to_period("M")

    # Agrupar y sumar por mes
    ventas_mensuales = df_filtrado_modelo.groupby([
        "Codigo_Local", "Codigo_Repuesto", "Mes"
    ])["Cantidad"].sum().reset_index()

    # Codificar categóricas
    ventas_mensuales["Codigo_Repuesto"] = ventas_mensuales["Codigo_Repuesto"].astype("category")
    ventas_mensuales["Repuesto_ID"] = ventas_mensuales["Codigo_Repuesto"].cat.codes
    ventas_mensuales["Mes_Num"] = ventas_mensuales["Mes"].astype(str).str.replace("-", "").astype(int)

    # Filtrar local seleccionado
    ventas_local = ventas_mensuales[ventas_mensuales["Codigo_Local"] == local_seleccionado].copy()

    # 🔁 Agregar características adicionales
    ventas_local["Lag_1"] = ventas_local.groupby("Repuesto_ID")["Cantidad"].shift(1).fillna(0)
    ventas_local["Media_3m"] = ventas_local.groupby("Repuesto_ID")["Cantidad"].transform(lambda x: x.rolling(3, 1).mean()).fillna(0)

    # Entrenamiento
    X = ventas_local[["Repuesto_ID", "Mes_Num", "Lag_1", "Media_3m"]]
    y = ventas_local["Cantidad"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    modelo = GradientBoostingRegressor(n_estimators=100, learning_rate=0.1, random_state=42)
    modelo.fit(X_train, y_train)

    # Predicción próximo mes
    ultimo_mes = ventas_local["Mes_Num"].max()
    proximo_mes = (datetime.strptime(str(ultimo_mes), "%Y%m") + timedelta(days=32)).strftime("%Y%m")
    proximo_mes = int(proximo_mes[:4] + proximo_mes[5:])

    # Crear predicciones para todos los repuestos activos
    repuestos_ids = ventas_local["Repuesto_ID"].unique()
    X_pred = pd.DataFrame({
        "Repuesto_ID": repuestos_ids,
        "Mes_Num": proximo_mes
    })

    # Obtener Lag_1 y Media_3m reales
    lag_map = ventas_local.groupby("Repuesto_ID")["Cantidad"].last().to_dict()
    media_map = ventas_local.groupby("Repuesto_ID")["Cantidad"].apply(lambda x: x.tail(3).mean()).to_dict()

    X_pred["Lag_1"] = X_pred["Repuesto_ID"].map(lag_map).fillna(0)
    X_pred["Media_3m"] = X_pred["Repuesto_ID"].map(media_map).fillna(0)

    # Predicción
    predicciones = modelo.predict(X_pred)

    # Mapear códigos
    codigo_map = dict(zip(ventas_local["Repuesto_ID"], ventas_local["Codigo_Repuesto"]))
    X_pred["Codigo_Repuesto"] = X_pred["Repuesto_ID"].map(codigo_map)
    X_pred["Prediccion_Unidades"] = predicciones.astype(int)
    X_pred["Mes"] = pd.to_datetime(str(proximo_mes), format="%Y%m").to_period("M")

    # Mostrar
    st.write("🔮 Predicción de unidades a vender en el próximo mes:")
    st.dataframe(X_pred[["Codigo_Repuesto", "Mes", "Prediccion_Unidades"]].sort_values("Prediccion_Unidades", ascending=False))

    # Error por producto
    error_df = pd.DataFrame({
        "Codigo_Repuesto": X_test["Repuesto_ID"].map(codigo_map),
        "Real": y_test,
        "Predicho": modelo.predict(X_test)
    })
    error_df["Error_Absoluto"] = abs(error_df["Real"] - error_df["Predicho"])

    #st.subheader("⚠️ Productos con mayor error de predicción")
    #st.dataframe(error_df.sort_values("Error_Absoluto", ascending=False).head(10))


    # Ejecutar Streamlit con:
    # streamlit run nombre_del_archivo.py

# -----------------------------------------------------------
# Cerrar sesión
# -----------------------------------------------------------

if st.button("Cerrar sesión"):
    st.session_state.logged_in = False
    st.rerun()

