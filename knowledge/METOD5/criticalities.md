# METOD5 - Reglas de criticidad

## Principio general

La criticidad en METOD5 depende de cuanto afecta la brecha a la confiabilidad del proceso de construccion, seleccion o sustentacion del modelo.

Una observacion es mas critica cuando la brecha puede cambiar la seleccion del modelo, sesgar la validacion, ocultar falta de materialidad o impedir que el revisor confie en la bondad de ajuste reportada.

## Criticidad alta

Asignar criticidad alta cuando ocurra cualquiera de estas condiciones y el modelo se use para decisiones materiales:

| Condicion | Razon |
|---|---|
| No existe evidencia de suficiencia minima de observaciones en Train, Dev y Test. | No se puede concluir que la construccion tenga base estadistica suficiente. |
| No existe evidencia de suficiencia minima de target en Train, Dev y Test. | La validacion puede no tener materialidad para evaluar el evento objetivo. |
| Train, Dev y Test no son comparables y no existe justificacion. | La seleccion del modelo puede estar basada en muestras no representativas. |
| Test/OOT fue usado en entrenamiento o validacion de modelos ensamblados. | Existe fuga metodologica y la performance puede estar sobreestimada. |
| El modelo fue seleccionado sin evidencia de tuneo o comparacion suficiente cuando se trata de ML. | No se sustenta que el modelo elegido sea razonable frente a alternativas. |
| No existe metrica de bondad de ajuste ni nivel de aceptacion para un modelo tradicional. | No se puede validar el sustento cuantitativo del modelo. |

## Criticidad media

Asignar criticidad media cuando hay evidencia parcial, pero el sustento metodologico es incompleto.

Ejemplos:

- El tuneo ML existe, pero no documenta el rango de hiperparametros evaluado.
- Se evaluaron menos de 50 combinaciones sin justificar por que ese rango era suficiente.
- La metrica de bondad de ajuste esta reportada, pero no se documenta el umbral o nivel de aceptacion.
- Hay analisis de Train, Dev y Test, pero falta una comparacion clara por target o variables finalistas.
- El ajuste por moras tempranas esta descrito, pero no se sustenta la seleccion de ventanas.
- Hay variaciones cercanas o superiores a 5 puntos de Gini de un mes a otro y la explicacion es incompleta.

## Criticidad baja

Asignar criticidad baja cuando la brecha es documental o de trazabilidad y no hay evidencia de impacto en la seleccion del modelo.

Ejemplos:

- Falta una explicacion secundaria, pero los conteos y metricas principales son consistentes.
- La metrica de bondad de ajuste esta sustentada, pero la redaccion del nivel de aceptacion es poco clara.
- La no aplicabilidad de ajuste por moras tempranas se infiere del informe, pero no esta declarada explicitamente.
- Hay pequenas inconsistencias de nomenclatura entre Train, Dev, Test y OOT, pero las muestras son identificables.

## Sin observacion

No generar observacion cuando:

- Las muestras cumplen materialidad suficiente o tienen excepcion justificada.
- Train, Dev y Test son similares por target y variables finalistas.
- No hay reutilizacion indebida de Test/OOT.
- El tuneo ML esta documentado y es suficientemente amplio, cuando aplica.
- La discriminacion y calibracion durante tuneo son estables.
- Los modelos tradicionales documentan supuestos, parametros, metrica y nivel de aceptacion.
- Las excepciones estan explicadas y no cambian la conclusion metodologica.

## Evidencia insuficiente

Si la evidencia no permite asignar criticidad, el resultado debe indicar informacion faltante en vez de inventar una conclusion.

La informacion faltante puede incluir:

- Conteos de observaciones por muestra.
- Conteos de target por muestra.
- Distribucion del target entre muestras.
- Distribucion de variables finalistas entre muestras.
- Listado de hiperparametros evaluados.
- Identificacion de Test/OOT.
- Metrica de bondad de ajuste y umbral de aceptacion.
