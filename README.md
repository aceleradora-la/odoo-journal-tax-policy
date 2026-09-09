# Journal Tax Policy

Módulos de Odoo que permiten decidir, **a nivel de diario de Ventas o de Compras**, si los
documentos emitidos con ese diario llevan impuestos o no.

| | |
|---|---|
| **Módulos** | `account_journal_tax_policy` · `sale_journal_tax_policy` |
| **Licencia** | AGPL-3 |
| **Versiones** | 17.0, 18.0, 19.0 — Community y Enterprise (ver [Ramas](#ramas)) |

## Para qué sirve

Odoo siempre calcula los impuestos de una línea de factura a partir del producto (o de la
cuenta) y después los mapea con la posición fiscal. No hay forma estándar de decir
"este talonario no lleva IVA".

`account_journal_tax_policy` agrega el campo **Política de impuestos** al diario, en la
pestaña *Configuración avanzada*:

- **Estándar** — comportamiento de fábrica de Odoo, no cambia nada.
- **Nunca aplicar impuestos** — las líneas del documento se mantienen siempre sin
  impuestos, sin importar lo que digan el producto, la cuenta o la posición fiscal.

El campo solo se muestra en diarios de tipo Ventas y Compras. En la factura no se agrega
nada: la columna de impuestos simplemente queda vacía.

## Comportamiento

1. **Al crear una factura** con un diario "sin impuestos", las líneas nacen sin impuestos.
   Tampoco los agrega la posición fiscal.
2. **Si se cambia el diario** de una factura en borrador a uno "sin impuestos", se quitan
   los impuestos de las líneas existentes.
3. **Si se vuelve** a un diario normal, se recalculan los impuestos con la lógica estándar
   de Odoo (producto → posición fiscal).
4. Cambiar entre dos diarios normales **no** toca los impuestos, igual que en Odoo de
   fábrica: no se pisan los impuestos que un contador haya editado a mano.
5. Aplica tanto en la interfaz (onchange) como por código: importaciones, API externa y
   facturas generadas desde un pedido de venta o una orden de compra.

Los documentos ya publicados no se tocan.

### El campo técnico invisible

Los dos módulos agregan al formulario de la factura y al del pedido un único campo:

```xml
<field name="taxes_removed_by_journal" invisible="1"/>
```

No muestra absolutamente nada: sin etiqueta, sin espacio, invisible de verdad. Está ahí
porque el protocolo de `onchange` de Odoo solo hace ida y vuelta con el navegador usando
**los campos que están en la vista**.

Sin ese campo, la secuencia *diario sin impuestos → diario normal → guardar*, hecha sin
guardar en el medio, dejaba el documento sin impuestos de forma permanente: la marca que
recuerda "estos impuestos los sacamos nosotros" se perdía entre un `onchange` y el
siguiente, y al guardar el servidor recibía un diario normal con líneas de impuestos
vacíos, indistinguible de "el usuario los borró a mano". No hay forma de arreglarlo solo
del lado del servidor, porque el paso intermedio nunca llega a la base de datos.

### Precio unitario

El precio unitario **no se modifica**. Si un producto tiene impuestos incluidos en el
precio (`price_include`), al quitar el impuesto la línea conserva el precio tal cual: un
producto a $121 con IVA 21% incluido queda en $121 sin impuestos, no en $100.

## Pedidos de venta

`sale_journal_tax_policy` es un módulo puente que lleva la misma lógica al campo **Diario
de facturación** del pedido de venta. Se instala solo (`auto_install`) cuando están
instalados `account_journal_tax_policy` y `sale`; el módulo principal **no** depende de
`sale`.

Sin este puente la factura igual sale bien, porque el pedido le pasa su diario y los
impuestos se limpian al crearla. Lo que aporta es que **el pedido muestre el mismo total
que la factura que va a generar**, en vez de mostrar IVA que después desaparece.

Solo actúa cuando el diario está elegido explícitamente en el pedido. Si el campo está
vacío, el pedido se comporta de forma estándar, porque en ese caso la factura usará el
diario de ventas con la secuencia más baja y no queremos adivinar cuál es.

No aplica a compras: `purchase.order` no tiene campo de diario en Odoo estándar; ahí el
diario se elige recién en la factura.

## Cómo funciona por dentro

En facturas el punto de entrada es `account.move.line._get_computed_taxes()`, que es el
único embudo por el que Odoo 17, 18 y 19 derivan los impuestos de una línea: impuestos del
producto, impuestos de la cuenta y mapeo de la posición fiscal terminan todos ahí.
Sobreescribirlo cubre de una sola vez todos los caminos de recálculo.

En pedidos no existe ese embudo, así que el gancho es directamente el compute del campo de
impuestos de la línea. El override **no** lleva `@api.depends`: Odoo acumula las
dependencias de todos los métodos homónimos del MRO, así que las de origen se conservan, y
agregar `order_id.journal_id` sería aditivo y haría que cualquier cambio de diario pisara
impuestos editados a mano.

Como el campo de impuestos es un `compute` con `readonly=False`, un valor escrito
explícitamente gana sobre el compute — por eso `create()`/`write()` de la línea también
limpian los impuestos que llegan desde un pedido de venta, una orden de compra, una
importación o la API.

El campo técnico `taxes_removed_by_journal` (en `account.move` y en `sale.order`) recuerda
que fuimos nosotros los que vaciamos los impuestos, y es lo que permite restaurarlos si el
diario vuelve a cambiar. Va en la vista como campo invisible para que sobreviva a los
`onchange`, ver [arriba](#el-campo-técnico-invisible).

## Ramas

Una rama por versión de Odoo:

| Rama | Odoo |
|---|---|
| `17.0` | 17.0 |
| `18.0` | 18.0 |
| `19.0` | 19.0 |

`account_journal_tax_policy` es idéntico en las tres. En `sale_journal_tax_policy` cambian
dos identificadores, porque Odoo renombró el campo en 19.0:

| | 17.0 / 18.0 | 19.0 |
|---|---|---|
| Campo | `sale.order.line.tax_id` | `sale.order.line.tax_ids` |
| Compute | `_compute_tax_id` | `_compute_tax_ids` |

## Instalación

```bash
git clone -b 19.0 https://github.com/aceleradora-la/odoo-journal-tax-policy.git
```

Agregar la carpeta al `addons_path`, actualizar la lista de aplicaciones e instalar
**Journal Tax Policy**. Si el módulo Ventas está instalado, el puente se agrega solo.

## Tests

```bash
odoo-bin -d <base> -i account_journal_tax_policy,sale_journal_tax_policy --test-enable \
    --test-tags /account_journal_tax_policy,/sale_journal_tax_policy --stop-after-init
```

## Autor

[aceleradora.la](https://aceleradora.la)
