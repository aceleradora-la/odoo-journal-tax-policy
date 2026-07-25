# Journal Tax Policy

Módulo de Odoo que permite decidir, **a nivel de diario de Ventas o de Compras**, si los
documentos emitidos con ese diario llevan impuestos o no.

| | |
|---|---|
| **Módulo** | `account_journal_tax_policy` |
| **Depende de** | `account` |
| **Licencia** | AGPL-3 |
| **Versiones** | 17.0, 18.0, 19.0 — Community y Enterprise (ver [Ramas](#ramas)) |

## Para qué sirve

Odoo siempre calcula los impuestos de una línea de factura a partir del producto (o de la
cuenta) y después los mapea con la posición fiscal. No hay forma estándar de decir
"este talonario no lleva IVA".

Este módulo agrega el campo **Política de impuestos** al diario:

- **Estándar** — comportamiento de fábrica de Odoo, no cambia nada.
- **Nunca aplicar impuestos** — las líneas del documento se mantienen siempre sin
  impuestos, sin importar lo que digan el producto, la cuenta o la posición fiscal.

El campo solo se muestra en diarios de tipo Ventas y Compras.

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

### Precio unitario

El precio unitario **no se modifica**. Si un producto tiene impuestos incluidos en el
precio (`price_include`), al quitar el impuesto la línea conserva el precio tal cual: un
producto a $121 con IVA 21% incluido queda en $121 sin impuestos, no en $100.

## Cómo funciona por dentro

El punto de entrada es `account.move.line._get_computed_taxes()`, que es el único embudo
por el que Odoo 17, 18 y 19 derivan los impuestos de una línea: impuestos del producto,
impuestos de la cuenta y mapeo de la posición fiscal terminan todos ahí. Sobreescribirlo
cubre de una sola vez todos los caminos de recálculo.

Como `tax_ids` es un campo `compute` con `readonly=False`, un valor escrito explícitamente
gana sobre el compute — por eso `account.move.line.create()/write()` también limpian los
impuestos que llegan desde un pedido de venta, una orden de compra o la API.

El campo técnico `account.move.taxes_removed_by_journal` recuerda que fuimos nosotros los
que vaciamos los impuestos, y es lo que permite restaurarlos si el diario vuelve a cambiar.

## Ramas

Una rama por versión de Odoo, con el mismo código:

| Rama | Odoo |
|---|---|
| `17.0` | 17.0 |
| `18.0` | 18.0 |
| `19.0` | 19.0 |

## Instalación

```bash
git clone -b 19.0 https://github.com/aceleradora-la/odoo-journal-tax-policy.git
```

Agregar la carpeta al `addons_path`, actualizar la lista de aplicaciones e instalar
**Journal Tax Policy**.

## Tests

```bash
odoo-bin -d <base> -i account_journal_tax_policy --test-enable --test-tags /account_journal_tax_policy --stop-after-init
```

## Autor

[Aceleradora-Latam](https://github.com/aceleradora-la)
