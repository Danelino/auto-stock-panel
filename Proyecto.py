import streamlit as st  
import numpy as np
import pandas as pd  
import matplotlib.pyplot as plt  
import seaborn as sns  
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from datetime import datetime, timedelta

# Carga los datos de usuarios desde un archivo CSV

def cargar_usuarios():
    try:
        return pd.read_csv("usuarios.csv")
    except FileNotFoundError:
        st.error("Archivo de usuarios no encontrado.")
        return pd.DataFrame(columns=["usuario", "contraseña"])

 # Inicialización de sesión

def login():
    st.title("🔐 Inicio de Sesión")
    usuarios_df = cargar_usuarios()

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "login_attempted" not in st.session_state:
        st.session_state.login_attempted = False

# Formulario de login

    if not st.session_state.logged_in:
        usuario = st.text_input("Usuario")
        contraseña = st.text_input("Contraseña", type="password")

        if st.button("Iniciar sesión") or st.session_state.login_attempted:
            st.session_state.login_attempted = True
            if not usuarios_df.empty:
                validacion = usuarios_df[
                    (usuarios_df["usuario"] == usuario) &
                    (usuarios_df["contraseña"] == contraseña)
                ]
                if not validacion.empty:
                    st.session_state.logged_in = True
                    st.success(f"Bienvenido, {usuario}")
                    st.session_state.login_attempted = False
                    st.session_state.usuario = usuario
                else:
                    st.error("Usuario o contraseña incorrectos")
            else:
                st.error("No hay usuarios registrados.")
    else:
        st.success(f"Sesión iniciada como: {st.session_state.usuario}")
        return True

    return st.session_state.logged_in


if login():
    st.sidebar.write(f"👤 Usuario: {st.session_state.usuario}")

    # Menú lateral para elegir la sección a mostrar

    menu = st.sidebar.radio("Navegación", [
        "Datos Ventas",
        "Top 50 Productos",
        "Recomendación Stock",
        "Ventas por Marca",
        "Predicción Demanda"
    ])

    # Carga de archivos de ventas, inventario y catálogo

    df = pd.read_csv("datos2020-2025.csv", sep=";", parse_dates=["Fecha_Venta"],
                    names=["Codigo_Boleta", "Codigo_Local", "Codigo_Repuesto", "Cantidad", "Fecha_Venta"])

    inventario = pd.read_csv("inventario.csv", sep=";",
                            names = ["Codigo_Local", "Codigo_Repuesto", "Cantidad_Stock"] )

    catalogo = pd.read_csv("Familia.csv", sep=";", names =["Letra", "Marca"])

    inventario["Cantidad_Stock"] = inventario["Cantidad_Stock"].apply(lambda x: x if x >= 0 else 0)

    # Selección de local y filtrado por fechas

    locales = df["Codigo_Local"].unique()
    local_seleccionado = st.sidebar.selectbox("Selecciona un Local", locales)

    df_filtrado = df[df["Codigo_Local"] == local_seleccionado]

    fecha_min, fecha_max = df_filtrado["Fecha_Venta"].min(), df_filtrado["Fecha_Venta"].max()
    fecha_inicio, fecha_fin = st.sidebar.date_input("Rango de Fechas", [fecha_min, fecha_max])

    df_filtrado = df_filtrado[(df_filtrado["Fecha_Venta"] >= pd.Timestamp(fecha_inicio)) & 
                            (df_filtrado["Fecha_Venta"] <= pd.Timestamp(fecha_fin))]

    #Sección: Datos Ventas

    if menu == "Datos Ventas":
        st.title("📌 Datos Filtrados (Ventas)")
        st.dataframe(df_filtrado)

    #Sección: Top 50 Productos Más Vendidos

    elif menu == "Top 50 Productos":
        st.title("🔥 Top 50 Productos Más Vendidos")
        top_50_productos = df_filtrado.groupby("Codigo_Repuesto")["Cantidad"].sum().sort_values(ascending=False).head(50)
        fig, ax = plt.subplots(figsize=(12, 6))
        sns.barplot(x=top_50_productos.index, y=top_50_productos.values, ax=ax, palette="Blues_r")
        plt.xticks(rotation=90)
        plt.xlabel("Código de Repuesto")
        plt.ylabel("Cantidad Vendida")
        st.pyplot(fig)

    #Sección: Recomendación de Stock

    elif menu == "Recomendación Stock":

        # Enriquecimiento de datos con la marca del repuesto
        df_filtrado["Marca_Letra"] = df_filtrado["Codigo_Repuesto"].astype(str).str[0]
        df_filtrado = df_filtrado.merge(catalogo, left_on="Marca_Letra", right_on="Letra", how="left")

        ventas_agrupadas = df_filtrado.groupby(["Codigo_Local", "Codigo_Repuesto"])["Cantidad"].sum().reset_index()
        ventas_agrupadas.rename(columns={"Cantidad": "Cantidad_Vendida"}, inplace=True)

        # Fusión con inventario
        inventario_local = inventario[inventario["Codigo_Local"] == local_seleccionado]
        df_inventario = pd.merge(inventario_local, ventas_agrupadas, on=["Codigo_Local", "Codigo_Repuesto"], how="left")
        df_inventario["Cantidad_Vendida"] = df_inventario["Cantidad_Vendida"].fillna(0)
        df_inventario["Rotacion"] = df_inventario["Cantidad_Vendida"] / (df_inventario["Cantidad_Stock"] + 1)

        df_inventario = df_inventario[~((df_inventario["Cantidad_Stock"] == 0) & (df_inventario["Cantidad_Vendida"] == 0))]

        # Clasificación según rotación
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

        # Productos vendidos con stock negativo (indicador de oportunidad de compra)
        ventas_sin_stock = df_filtrado[df_filtrado["Cantidad"] < 0]
        recomendaciones_compra = ventas_sin_stock.groupby("Codigo_Repuesto")["Cantidad"].count().reset_index()
        recomendaciones_compra.rename(columns={"Cantidad": "Intentos_Fallidos"}, inplace=True)
        recomendaciones_compra["Recomendacion"] = "🔄 Evaluar su compra"

        cantidad_a_mostrar = st.sidebar.selectbox(
            "¿Cuántos productos quieres visualizar por sección?",
            options=[10, 20, 50, 100, len(df_inventario)],
            index=0
        )

        st.subheader("✅ Productos con buena rotación (conviene mantener):")
        st.dataframe(df_inventario[df_inventario["Recomendacion"] == "✅ Mantener en stock"]
                    .sort_values("Rotacion", ascending=False).head(cantidad_a_mostrar))

        st.subheader("🛒 Repuestos Recomendados para Comprar (por ventas sin stock):")
        if not recomendaciones_compra.empty:    
            st.dataframe(recomendaciones_compra.sort_values("Intentos_Fallidos", ascending=False).head(cantidad_a_mostrar))
        else:
            st.write("✅ No se encontraron intentos de venta fallida por falta de stock en el período seleccionado.")

        st.subheader("⚠️ Productos con stock sin ventas:")
        st.dataframe(df_inventario[df_inventario["Recomendacion"] == "⚠️ Revisar (stock sin ventas)"]
                    .sort_values("Cantidad_Stock", ascending=False).head(cantidad_a_mostrar))

    #Sección: Ventas por Marca
    elif menu == "Ventas por Marca":
        df_filtrado["Marca_Letra"] = df_filtrado["Codigo_Repuesto"].astype(str).str[0]
        df_filtrado = df_filtrado.merge(catalogo, left_on="Marca_Letra", right_on="Letra", how="left")
        ventas_marca_local = df_filtrado.groupby(["Codigo_Local", "Marca"])["Cantidad"].sum().reset_index()
        ventas_marca_local = ventas_marca_local.sort_values(["Codigo_Local", "Cantidad"], ascending=[True, False])

        st.subheader("🏷️ Ventas Totales por Marca y Local")
        st.dataframe(ventas_marca_local)

        df_local_marca = ventas_marca_local[ventas_marca_local["Codigo_Local"] == local_seleccionado]
        fig, ax = plt.subplots(figsize=(20, 5))
        sns.barplot(data=df_local_marca, x="Marca", y="Cantidad", ax=ax, palette="viridis")
        plt.title(f"🔝 Marcas más vendidas - Local {local_seleccionado}")
        plt.xticks(rotation=45)
        plt.xlabel("Marca")
        plt.ylabel("Cantidad Vendida")
        st.pyplot(fig)
    
    #Sección: Predicción de Demanda
    elif menu == "Predicción Demanda":
        st.title("📈 Predicción de Demanda con ML")
        
        # Copia del DataFrame filtrado
        df_filtrado_modelo = df_filtrado.copy()
        df_filtrado_modelo["Mes"] = df_filtrado_modelo["Fecha_Venta"].dt.to_period("M")

        # Agregación mensual por local y producto
        ventas_mensuales = df_filtrado_modelo.groupby([
            "Codigo_Local", "Codigo_Repuesto", "Mes"
        ])["Cantidad"].sum().reset_index()

        # Codificación
        ventas_mensuales["Codigo_Repuesto"] = ventas_mensuales["Codigo_Repuesto"].astype("category")
        ventas_mensuales["Repuesto_ID"] = ventas_mensuales["Codigo_Repuesto"].cat.codes
        ventas_mensuales["Mes_Num"] = ventas_mensuales["Mes"].astype(str).str.replace("-", "").astype(int)

        # Filtrar por local seleccionado
        ventas_local = ventas_mensuales[ventas_mensuales["Codigo_Local"] == local_seleccionado].copy()

        # Orden por tiempo para aplicar lag y rolling correctamente
        ventas_local = ventas_local.sort_values(["Repuesto_ID", "Mes_Num"])

        # Ingeniería de características: Lag y Media Móvil
        ventas_local["Lag_1"] = ventas_local.groupby("Repuesto_ID")["Cantidad"].shift(1).fillna(0)
        ventas_local["Media_3m"] = ventas_local.groupby("Repuesto_ID")["Cantidad"].transform(lambda x: x.rolling(3, 1).mean()).fillna(0)

        # Entrenamiento del modelo
        X = ventas_local[["Repuesto_ID", "Mes_Num", "Lag_1", "Media_3m"]]
        y = ventas_local["Cantidad"]
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        modelo = GradientBoostingRegressor(n_estimators=100, learning_rate=0.1, random_state=42)
        modelo.fit(X_train, y_train)

        # Evaluación del modelo 
        y_pred_test = modelo.predict(X_test)

        mae = mean_absolute_error(y_test, y_pred_test)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
        r2 = r2_score(y_test, y_pred_test)

        st.subheader("📊 Evaluación del Modelo:")
        st.write("MAE:", round(mae, 2))
        st.write("RMSE:", round(rmse, 2))
        st.write("R²:", round(r2, 3))

        # Preparar predicción del próximo mes
        ultimo_mes = ventas_local["Mes_Num"].max()
        proximo_mes = (datetime.strptime(str(ultimo_mes), "%Y%m") + timedelta(days=32)).strftime("%Y%m")
        proximo_mes = int(proximo_mes[:4] + proximo_mes[5:])

        # Crear nuevo dataset para predecir el próximo mes
        repuestos_ids = ventas_local["Repuesto_ID"].unique()
        codigo_repuestos = ventas_local.drop_duplicates("Repuesto_ID")[["Repuesto_ID", "Codigo_Repuesto"]]

        # Obtener último Lag y media para cada Repuesto_ID
        ultimos_valores = ventas_local.groupby("Repuesto_ID").last().reset_index()
        X_pred = pd.DataFrame({
            "Repuesto_ID": ultimos_valores["Repuesto_ID"],
            "Mes_Num": proximo_mes,
            "Lag_1": ultimos_valores["Cantidad"],
            "Media_3m": ultimos_valores["Media_3m"]
        })

        # Predicción
        predicciones = modelo.predict(X_pred)

        resultados_pred = pd.DataFrame({
            "Repuesto_ID": X_pred["Repuesto_ID"],
            "Demanda_Prevista": predicciones
        }).merge(codigo_repuestos, on="Repuesto_ID")

        resultados_pred = resultados_pred.sort_values("Demanda_Prevista", ascending=False)

        st.subheader("📈 Predicción de Demanda para el Próximo Mes")
        st.dataframe(resultados_pred.head(50))
