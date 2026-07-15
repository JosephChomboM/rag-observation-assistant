# METOD5 - Bondad de ajuste, muestras y modelamiento

## Proposito

METOD5 valida si la etapa de construccion y seleccion del modelo tiene una base estadistica suficiente, trazable y metodologicamente consistente antes de evaluar el modelo final en produccion o seguimiento.

Este metodo se enfoca en la calidad de las muestras Train, Dev y Test, la suficiencia de observaciones y eventos target, la separacion correcta de muestras, la razonabilidad del tuneo de modelos ML y la evidencia usada para sustentar la bondad de ajuste de modelos tradicionales.

## Alcance metodologico

METOD5 cubre principalmente:

- Suficiencia de observaciones en Train, Dev y Test.
- Suficiencia de casos target en Train, Dev y Test.
- Similitud entre muestras usando el target y las variables finalistas.
- Separacion entre muestras de entrenamiento/validacion de modelos ensamblados y la muestra Test/OOT del modelo final.
- Coherencia metodologica en ajustes por moras tempranas, cuando apliquen.
- Tuneo de modelos ML y estabilidad de discriminacion/calibracion durante la seleccion del modelo.
- Cumplimiento de supuestos, parametros y metricas de bondad de ajuste en modelos tradicionales.

## Preguntas de revision

El revisor debe usar METOD5 para responder:

- El modelo fue construido con suficiente volumen de datos y suficiente materialidad de target?
- Las muestras Train, Dev y Test son comparables entre si?
- Existe fuga metodologica por reutilizar Test/OOT en entrenamiento o validacion?
- El tuneo ML fue suficientemente amplio y documentado?
- La seleccion del modelo esta sustentada por estabilidad de discriminacion y calibracion?
- En modelos tradicionales, se justifico la metrica de bondad de ajuste y su nivel de aceptacion?
- Las excepciones metodologicas estan justificadas y documentadas?

## Evidencia esperada

La evidencia deberia incluir, segun aplique:

- Conteo de observaciones por muestra Train, Dev y Test.
- Conteo de eventos target por muestra Train, Dev y Test.
- Comparacion de distribucion del target entre muestras.
- Comparacion de distribucion de variables finalistas entre muestras.
- Identificacion de muestras usadas para entrenamiento, validacion, Test y OOT.
- Resumen de hiperparametros evaluados y criterio de seleccion del mejor modelo.
- Evolucion mensual de Gini y calibracion del modelo seleccionado frente al mejor modelo validado.
- Sustento de metrica de bondad de ajuste para modelos tradicionales.
- Evidencia de supuestos estadisticos, parametros estimados o parametrizacion de arboles, cuando aplique.

## Contexto del modelo

La informacion especifica del modelo validado no debe escribirse en este archivo de knowledge. Debe llegar como contexto runtime por widgets del notebook, por ejemplo:

- `model_name`
- `model_type`
- `model_tier`
- `application_type`
- `model_usage`
- `target_variable`
- `time_variable`
- `amount_variable`

El knowledge de METOD5 define los criterios estables. Los widgets describen el caso concreto que se esta validando.

## Fuente del checklist

Este archivo resume la hoja `METOD 5` de `checklist_scoring_vi.md`, cuyo tema aproximado es `Bondad de ajuste, muestras y modelamiento`.

Referencias principales:

- Fila 4: suficiencia de observaciones en Train, Dev y Test.
- Fila 5: suficiencia de target en Train, Dev y Test.
- Filas 6 y 7: similitud de muestras usando target y variables finalistas.
- Fila 9: separacion de muestras para modelos ensamblados ML.
- Filas 11 y 12: ajuste de moras tempranas, si aplica.
- Filas 14 y 15: tuneo ML y estabilidad de discriminacion/calibracion.
- Filas 17 a 31: requisitos, supuestos, parametros y metricas de bondad de ajuste para modelos tradicionales.
