# Tablas SUNAT (Anexo 3 de la RS 286-2009 y modificatorias) que usa el 13.1.
# Se declaran como Selection y no como modelos para no traer el modulo
# completo de tablas SUNAT: el cliente solo lleva este libro.

# Tabla 5: Tipo de existencia (campo 6)
TABLA_05 = [
    ('01', '01 - Mercaderías'),
    ('02', '02 - Productos terminados'),
    ('03', '03 - Materias primas'),
    ('04', '04 - Envases'),
    ('05', '05 - Materiales auxiliares'),
    ('06', '06 - Suministros'),
    ('07', '07 - Repuestos'),
    ('08', '08 - Embalajes'),
    ('09', '09 - Subproductos'),
    ('10', '10 - Desechos y desperdicios'),
    ('91', '91 - Otros 1'),
    ('92', '92 - Otros 2'),
    ('93', '93 - Otros 3'),
    ('94', '94 - Otros 4'),
    ('95', '95 - Otros 5'),
    ('96', '96 - Otros 6'),
    ('97', '97 - Otros 7'),
    ('98', '98 - Otros 8'),
    ('99', '99 - Otros'),
]

# Tabla 12: Tipo de operacion (campo 14)
TABLA_12 = [
    ('01', '01 - Venta nacional'),
    ('02', '02 - Compra nacional'),
    ('03', '03 - Consignación recibida'),
    ('04', '04 - Consignación entregada'),
    ('05', '05 - Devolución recibida'),
    ('06', '06 - Devolución entregada'),
    ('07', '07 - Bonificación'),
    ('08', '08 - Premio'),
    ('09', '09 - Donación'),
    ('10', '10 - Salida a producción'),
    ('11', '11 - Salida por transferencia entre almacenes'),
    ('12', '12 - Retiro'),
    ('13', '13 - Mermas'),
    ('14', '14 - Desmedros'),
    ('15', '15 - Destrucción'),
    ('16', '16 - Saldo inicial'),
    ('17', '17 - Exportación'),
    ('18', '18 - Importación'),
    ('19', '19 - Entrada de producción'),
    ('20', '20 - Entrada por devolución de producción'),
    ('21', '21 - Entrada por transferencia entre almacenes'),
    ('22', '22 - Entrada por identificación errónea'),
    ('23', '23 - Salida por identificación errónea'),
    ('24', '24 - Entrada por devolución del cliente'),
    ('25', '25 - Salida por devolución al proveedor'),
    ('26', '26 - Entrada para servicio de producción'),
    ('27', '27 - Salida por servicio de producción'),
    ('28', '28 - Ajuste por diferencia de inventario'),
    ('29', '29 - Entrada de bienes en préstamo'),
    ('30', '30 - Salida de bienes en préstamo'),
    ('31', '31 - Entrada de bienes en custodia'),
    ('32', '32 - Salida de bienes en custodia'),
    ('33', '33 - Muestras médicas'),
    ('34', '34 - Publicidad'),
    ('35', '35 - Gastos de representación'),
    ('36', '36 - Retiro para entrega a trabajadores'),
    ('37', '37 - Retiro por convenio colectivo'),
    ('38', '38 - Retiro por sustitución de bien siniestrado'),
    ('91', '91 - Otros 1'),
    ('92', '92 - Otros 2'),
    ('93', '93 - Otros 3'),
    ('94', '94 - Otros 4'),
    ('95', '95 - Otros 5'),
    ('96', '96 - Otros 6'),
    ('97', '97 - Otros 7'),
    ('98', '98 - Otros 8'),
    ('99', '99 - Otros'),
]

# Operaciones que SUNAT obliga a sustentar con documento: si el campo 14 es
# una de estas, el campo 11 no puede ser '00' (RS 108-2020, Formato 13.1).
OPERACIONES_CON_DOCUMENTO = ('01', '02', '03', '04', '05', '06')

# Campo 17 (Tabla 14), deducido del metodo de costeo real de la categoria:
#   1 PROMEDIO PONDERADO   2 PEPS   9 OTROS
# El costo estandar de Odoo no tiene equivalente en la Tabla 14 -> 9 OTROS.
COST_METHOD_TO_TABLA_14 = {
    'average': '1',
    'fifo': '2',
    'standard': '9',
}
