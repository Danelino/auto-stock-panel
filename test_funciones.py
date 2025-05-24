# test_funciones.py
from funciones import clasificar_rotacion

def test_clasificar_rotacion_mantener():
    resultado = clasificar_rotacion(50, 10, 5.0, 3.0, 1.0)
    assert resultado == "✅ Mantener en stock"

def test_clasificar_rotacion_revisar():
    resultado = clasificar_rotacion(5, 20, 0.5, 3.0, 1.0)
    assert resultado == "⚠️ Revisar"

def test_clasificar_rotacion_stock_sin_ventas():
    resultado = clasificar_rotacion(0, 15, 0.0, 3.0, 1.0)
    assert resultado == "⚠️ Revisar (stock sin ventas)"

def test_clasificar_rotacion_indefinido():
    resultado = clasificar_rotacion(10, 5, 2.0, 3.0, 1.0)
    assert resultado == "❓ Evaluar"
