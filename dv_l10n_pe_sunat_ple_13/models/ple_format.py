def format_positive_value(value, decimals, positive=True):
    """Formatea un importe o cantidad del 13.1 como lo exige el validador.

    Tres reglas, las tres confirmadas por el reporte de inconsistencias del
    PVS y por la implementacion nativa de Odoo (l10n_pe_reports_stock):

    1. El CERO se escribe siempre '0.00', sin importar los decimales del
       campo. El PVS rechaza '0.00000000' con "Si consigna cero debe ser
       0.00".

    2. Los campos de ingreso, retiro y saldo van en POSITIVO. La direccion
       del movimiento la da la columna, no el signo. El PVS rechazaba
       '- 1.00000000' en el campo 21 con "Formato incorrecto".

    3. Nunca se emite el signo separado por un espacio.

    El parametro 'positive' se conserva por compatibilidad con las llamadas
    existentes, pero ya no cambia el resultado: todo sale en positivo.
    """
    value = round(value or 0.0, decimals)
    if not value:
        return '0.00'
    return format(abs(value), '.{}f'.format(decimals))


def sanitize_ple_code(product, largo=24):
    """Codigo propio de la existencia (campo 7).

    El PVS marca "Formato incorrecto" si la referencia lleva caracteres no
    alfanumericos (PR/00829), y el campo 7 forma parte de la llave unica.
    Un producto sin referencia interna se identifica por su id: con un
    codigo fijo todos esos productos se fundirian en una sola existencia.
    """
    limpio = ''.join(c for c in (product.default_code or '') if c.isalnum())
    return limpio[:largo] or str(product.id)


def sanitize_ple_text(text, largo):
    """Texto libre sin '|' ni saltos de linea: cualquiera de los dos
    descuadra el registro completo del TXT."""
    text = ' '.join((text or '').replace('|', ' ').split())
    return text[:largo].strip()


def product_ple_fields(product):
    """Campos 5 a 9 del 13.1, comunes al saldo inicial y a los movimientos.

    Deben salir identicos en ambos: si difieren, SUNAT ve dos existencias
    distintas y el saldo inicial no enlaza con su Kardex.
    """
    unspsc = product.unspsc_code_id.code or ''
    return [
        # 5 Catalogo del codigo del campo 7: el codigo propio -> 9 OTROS
        '9',
        # 6 Tipo de existencia (Tabla 5)
        product.l10n_pe_ple_existence_type or '01',
        # 7 Codigo propio de la existencia
        sanitize_ple_code(product),
        # 8-9 Codigo UNSPSC (catalogo 1 NACIONES UNIDAS). Es el mismo que la
        # factura electronica envia a SUNAT; desde el 01/01/2021 es
        # obligatorio si el comprobante lo consigno. Sin codigo, van vacios.
        '1' if unspsc else '',
        unspsc,
    ]


def product_ple_tail(product):
    """Campos 15 a 17 del 13.1."""
    return [
        # 15 Descripcion de la existencia
        sanitize_ple_text(product.display_name, 80) or 'Mercaderia',
        # 16 Unidad de medida (Tabla 6): mismo codigo que usa la factura electronica
        product.uom_id.l10n_pe_edi_measure_unit_code or 'NIU',
        # 17 Metodo de valuacion (Tabla 14)
        product.get_l10n_table_14_code(),
    ]
