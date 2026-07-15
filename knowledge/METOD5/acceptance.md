# METOD5 - Criterios de aceptacion

## Muestras Train, Dev y Test

Una revision METOD5 es aceptable cuando la evidencia muestra que las muestras Train, Dev y Test tienen materialidad suficiente para sustentar el desarrollo y la validacion del modelo.

| Control | Criterio de aceptacion | Fuente checklist |
|---|---|---|
| Suficiencia de observaciones | Mas de 1000 casos en Train, Dev y Test, cuando la cartera lo permita. | METOD5 fila 4 |
| Suficiencia de target | Mas de 450 casos target en Train, Dev y Test, cuando la cartera lo permita. | METOD5 fila 5 |
| Similitud por target | Las muestras Train, Dev y Test deben ser similares usando la variable target. | METOD5 fila 6 |
| Similitud por variables finalistas | Las muestras Train, Dev y Test deben ser similares usando las variables finalistas. | METOD5 fila 7 |

Si la cartera no permite alcanzar los minimos de observaciones o target, el caso puede ser aceptable solo si existe una justificacion metodologica explicita y se evalua un tratamiento alternativo, como pauta para esa poblacion.

## Modelos ensamblados ML

Para modelos ensamblados de machine learning, las muestras usadas en entrenamiento o validacion de los modelos base no deben coincidir con la muestra Test/OOT usada para la construccion o evaluacion del modelo final.

La aceptacion requiere evidencia clara de:

- Que muestra se uso para entrenamiento.
- Que muestra se uso para validacion.
- Que muestra se uso como Test.
- Que muestra se uso como OOT, si aplica.
- Que Test/OOT no fue reutilizada indebidamente en entrenamiento o validacion.

Fuente checklist: METOD5 fila 9.

## Ajuste de moras tempranas

Cuando el modelo incluya ajuste por moras tempranas, la metodologia para obtener factores debe ser coherente y usar un criterio estandar para todos los modelos comparables.

La aceptacion requiere:

- Logica de calculo de factores documentada.
- Ventanas seleccionadas de forma razonable.
- Evidencia de que las ventanas no introducen sesgo en el factor.
- Explicacion de por que el ajuste mejora o estabiliza la medicion esperada.

Si el ajuste por moras tempranas no aplica, el informe debe indicarlo explicitamente.

Fuente checklist: METOD5 filas 11 y 12.

## Tuneo de modelos ML

Para modelos ML, el tuneo es aceptable cuando se replica o valida una busqueda suficientemente amplia de hiperparametros.

| Control | Criterio de aceptacion | Fuente checklist |
|---|---|---|
| Amplitud de tuneo | Evaluar una gama mayor de hiperparametros, con minimo de 50 combinaciones cuando aplique. | METOD5 fila 14 |
| Varias etapas de tuneo | Si existe mas de una etapa de tuneo, cada etapa se evalua con el mismo criterio. | METOD5 fila 15 |
| Estabilidad | La discriminacion debe variar menos de 5 puntos de Gini de un mes a otro. | METOD5 fila 15 |
| Comparacion contra mejor modelo | El modelo seleccionado debe evaluarse contra el mejor modelo obtenido en la validacion. | METOD5 fila 15 |
| Calibracion durante seleccion | La calibracion del modelo seleccionado debe ser razonable frente al mejor modelo validado. | METOD5 fila 15 |

## Modelos tradicionales

Para modelos tradicionales, la aceptacion depende de que se documenten los requisitos minimos, supuestos, parametros y la metrica de bondad de ajuste usada.

El informe debe indicar la metrica y el nivel de aceptacion utilizado. Ejemplos de metricas aceptables, segun el tipo de modelo:

- R2.
- Gini.
- Entropia.
- RECM.
- Error absoluto.
- Porcentaje de aciertos.
- Otra metrica sustentada metodologicamente.

Fuente checklist: METOD5 filas 17 a 31.

## Condicion de no observacion

No se deberia generar observacion si la evidencia muestra que:

- Las muestras tienen materialidad suficiente o una excepcion justificada.
- Train, Dev y Test son similares por target y variables finalistas.
- No existe fuga por reutilizacion de Test/OOT en modelos ensamblados.
- El ajuste por moras tempranas esta justificado o no aplica.
- El tuneo ML es suficientemente amplio y estable, cuando aplica.
- Los modelos tradicionales documentan supuestos, parametros, metrica y nivel de aceptacion.
