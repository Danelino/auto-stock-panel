# funciones.py

def clasificar_rotacion(cantidad_vendida, cantidad_stock, rotacion, umbral_alto, umbral_bajo):
    if cantidad_vendida == 0 and cantidad_stock > 0:
        return "⚠️ Revisar (stock sin ventas)"
    elif rotacion >= umbral_alto:
        return "✅ Mantener en stock"
    elif rotacion <= umbral_bajo:
        return "⚠️ Revisar"
    else:
        return "❓ Evaluar"
