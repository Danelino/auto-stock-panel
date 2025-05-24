# 📊 Plataforma de Gestión y Análisis de Ventas e Inventario

---

## 🧩 Descripción

Esta plataforma permite la gestión centralizada de los datos de ventas e inventario de una empresa de repuestos automotrices, ofreciendo análisis visuales y predictivos para optimizar la toma de decisiones. 

Incluye funcionalidades como:

- Visualización de ventas por producto y local.
- Análisis de rotación de inventario.
- Seguimiento del comportamiento específico por local.
- Predicción mensual de demanda por producto y ubicación.

---

## 🎯 Objetivos del Proyecto

- Desarrollar una aplicación web interactiva desde una perspectiva estadística.
- Construir un panel para visualizar datos clave del negocio.
- Implementar un modelo predictivo que permita anticipar la demanda y reducir costos operativos.

---

## 🚀 Funcionalidades

- ✅ Inicio de sesión con validación de usuarios.
- ✅ Visualización de métricas clave de ventas e inventario.
- ✅ Filtros dinámicos por producto, local y fecha.
- ✅ Predicciones de demanda mensual utilizando modelos de datos.
- ✅ Carga y análisis automático de archivos `.csv`.

---

## 🛠️ Tecnologías utilizadas

- **Lenguaje:** Python 3.12
- **Framework:** [Streamlit](https://streamlit.io/)
- **Librerías:**  
  `pandas`, `numpy`, `matplotlib`, `seaborn`, `scikit-learn`

---

## 🧠 Modelo de Datos

**Tablas principales:**

- **Locales** (`ID_Local`, `Nombre_Local`)  
- **Repuestos** (`ID_Repuesto`, `Código`, `Descripción`)  
- **Ventas** (`ID_Venta`, `Fecha`, `Cantidad_Vendida`, `ID_Local`, `ID_Repuesto`)  
- **Predicciones** (`ID_Predicción`, `Mes`, `Unidades_Previstas`, `ID_Local`, `ID_Repuesto`)

