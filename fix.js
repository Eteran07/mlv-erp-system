@
const fs = require("fs");
let text = fs.readFileSync("frontend/src/pages/ExcelSync.jsx", "utf8");

const regex = /const BLOQUE_SUPERIOR = [\s\S]*?initialRowData\[i\] = itemRowData;/;
const replacement = `const BLOQUE_SUPERIOR = \`SOMOS TIENDA FÍSICA, Empresa Mayorista Líder en el Mercado de la Computación Producto 100% de calidad\`;
      const BLOQUE_INFERIOR = \`.
Por Favor Verifique la disponibilidad antes de ofertar
Por Favor Verifique la disponibilidad antes de ofertar
Por Favor Verifique la disponibilidad antes de ofertar
**************************************************************************************************
- Emitimos factura LEGAL
- Trabajamos con agentes de retención
- Enviamos a todo el País.
**************************************************************************************************
COMENTARIOS:
- Realice todas las preguntas necesarias Antes de ofertar.
- El equipo de ventas está a tu disposición para responder tus consultas.
- Te invitamos a que solo ofertes cuando estés seguro de realizar la compra.
- La disponibilidad y precio del producto publicado solo se garantiza por un lapso de 24hrs luego de haber solicitado la compra.
- Si presentas algún inconveniente durante el proceso de compras estaremos a tu completa disposición para atenderte y solventar la situación. Deseamos que tu compra con nosotros siempre genere una calificación positiva.
****************************************************************************************************
HORARIO DE TRABAJO
****************************************************
De Lunes A Viernes
De 8:30am A 5:30pm\`;

      (d.productos || []).forEach((p, i) => {
        const itemRowData = {};
        if (p.ImagenLocal) {
          itemRowData.localImages = [p.ImagenLocal];
        }
        
        // Auto-fill template
        let titulo = p.Titulo;
        let descFinal = \`\${BLOQUE_SUPERIOR}\\n\\n\${titulo}\\n\${titulo}\\n\${titulo}\\n\\n\`;
        const custom = p.DescripcionCustom || "";
        if (custom.trim().length > 5) descFinal += \`\${custom}\\n\\n\`;
        descFinal += \`========================================\\nCARACTERÍSTICAS TÉCNICAS\\n========================================\\n\\n\`;
        descFinal += \`========================================\\n\\n\${BLOQUE_INFERIOR}\`;
        
        itemRowData.descripcion = descFinal;
        initialRowData[i] = itemRowData;`;

text = text.replace(regex, replacement);
fs.writeFileSync("frontend/src/pages/ExcelSync.jsx", text, "utf8");
@