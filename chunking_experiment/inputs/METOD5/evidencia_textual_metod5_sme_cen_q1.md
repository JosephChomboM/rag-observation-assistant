# Evidencia textual consolidada - METOD5

## Contexto del modelo

Modelo evaluado: SME Calibrated Model CEN Q1.

Tipo de modelo: scoring.

Uso del modelo: applicant.

Aplicacion: CEN.

Tier: Tier I.

Variable target: DEFAULT12.

Variable temporal: CODMES.

Variable de monto: SALDO.

Esta evidencia textual se prepara como input de prueba para complementar las imagenes cargadas en el experimento METOD5. No reemplaza las imagenes originales ni el knowledge metodologico; solo resume los principales hallazgos visibles para probar retrieval y generacion de observaciones con evidencia mixta.

## Resumen de evidencia disponible

La documentacion revisada contiene graficos y tablas asociados a bondad de ajuste, estabilidad de performance, calibracion y revision de variables del modelo. Las imagenes muestran evidencia relacionada con:

- Evolucion mensual de Gini y estabilidad discriminatoria.
- Revision de pesos, coeficientes o signos esperados de variables.
- Reproduccion o coincidencia de parametros del modelo.
- Construccion de variables y transformaciones usadas durante el modelamiento.
- Calibracion OOT por segmentos, incluyendo vistas por LTV proforma, monto aprobado, cuentas y montos.
- Comparaciones entre default observado y default estimado.

## Estabilidad de discriminacion

Se observa una revision mensual del Gini para evaluar si la discriminacion del modelo se mantiene estable durante el periodo analizado. La evidencia permite identificar variaciones entre cortes mensuales, pero no queda completamente claro si el informe define un umbral formal de aceptacion para la variacion del Gini.

Para METOD5, esta evidencia es relevante porque la discriminacion debe mantenerse estable durante el modelamiento y la seleccion del modelo. Si la variacion mensual supera el nivel de tolerancia definido por la metodologia, deberia sustentarse la causa y el tratamiento aplicado.

## Calibracion y OOT

Las imagenes incluyen vistas de calibracion fuera de muestra u OOT. Se muestran comparaciones entre indicadores observados y estimados, con cortes por segmentos de negocio o variables relevantes como LTV proforma, monto aprobado, numero de cuentas y monto de exposicion.

La evidencia sugiere que se reviso la calibracion del modelo en diferentes agrupaciones. Sin embargo, para una revision completa se deberia confirmar:

- Periodo exacto de la muestra OOT.
- Definicion del target usado en la calibracion.
- Criterio de aceptacion usado para diferencias entre observado y estimado.
- Tratamiento aplicado cuando existen desviaciones relevantes por segmento.

## Variables, pesos y parametros

El material visual contiene evidencia sobre variables finalistas, pesos, coeficientes, signos esperados y construccion de variables. Esto permite revisar si las variables tienen sentido metodologico y si los parametros son consistentes con la logica de negocio.

Hay indicios de revision de coincidencia o reproduccion de coeficientes. Para cerrar la validacion se requiere confirmar que:

- Los coeficientes finales coinciden con el artefacto productivo o manual metodologico.
- Los signos de las variables estan justificados.
- Las variables seleccionadas cuentan con sustento estadistico o de negocio.
- Las transformaciones usadas en modelamiento estan documentadas.

## Modelamiento y seleccion

La evidencia parece combinar elementos de modelos tradicionales y validaciones de calibracion. Si el modelo fue seleccionado mediante criterios de negocio, debe existir acta, justificacion o registro formal en el manual metodologico.

Si el modelo corresponde a un enfoque tradicional, la revision debe enfocarse en supuestos, parametros, signos, pesos, bondad de ajuste y metrica de aceptacion. Si el modelo incluye componentes ML o ensamblados, se requiere evidencia adicional de tuneo, busqueda de hiperparametros y separacion adecuada de Train, Development, Test y OOT.

## Informacion faltante para cerrar METOD5

La evidencia textual y visual disponible no permite confirmar por completo los siguientes puntos:

- Cantidad total de observaciones usadas en Train, Development, Test y OOT.
- Cantidad de casos target o defaults por muestra.
- Comparabilidad estadistica entre Train, Development y Test usando target y variables finalistas.
- Separacion efectiva entre muestras de entrenamiento, validacion y OOT.
- Umbral formal de aceptacion para Gini, calibracion u otra metrica de bondad de ajuste.
- Sustento del criterio usado para elegir variables o versiones finales del modelo.

## Posible observacion preliminar

La documentacion presenta evidencia relevante de estabilidad, calibracion y revision de variables para el modelo SME Calibrated Model CEN Q1. No obstante, la validacion METOD5 podria quedar incompleta si el informe no documenta claramente los umbrales de aceptacion, los conteos de muestra y target, la comparabilidad Train/Development/Test y la justificacion formal de seleccion de variables o parametros.

La criticidad preliminar seria media si existen metricas y graficos de soporte, pero faltan umbrales o trazabilidad metodologica suficiente. Podria elevarse a alta si se confirma que no existe separacion adecuada de muestras, que se uso OOT para entrenamiento o que el modelo Tier I fue aprobado sin evidencia suficiente de muestra, target y bondad de ajuste.
