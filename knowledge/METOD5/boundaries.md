# METOD5 - Limites de aplicacion

## Cuando aplica

METOD5 aplica cuando se esta validando una etapa de construccion, seleccion o sustentacion metodologica del modelo.

Aplica a modelos de riesgo crediticio o relacionados, incluyendo:

- Scoring.
- PD.
- Rating.
- Alertas.
- Endeudamiento.
- Tasaciones.
- Estimadores.
- Segmentacion.

Tambien aplica a modelos applicant y behavior cuando exista una etapa de modelamiento con muestras de entrenamiento, desarrollo, validacion, Test u OOT.

## Modelos ML

En modelos ML, METOD5 aplica especialmente cuando hay:

- Tuneo de hiperparametros.
- Modelos ensamblados.
- Seleccion del mejor modelo entre alternativas.
- Comparacion de discriminacion o calibracion durante modelamiento.
- Validacion de estabilidad del modelo seleccionado frente al mejor modelo de la validacion.

El foco no es solo el valor final de la metrica. El foco es si el proceso usado para llegar al modelo seleccionado fue suficientemente robusto y trazable.

## Modelos tradicionales

En modelos tradicionales, METOD5 aplica cuando se usan estimadores, regresiones, arboles u otras tecnicas que requieren supuestos, parametros o metricas de ajuste.

Ejemplos:

- Regresion lineal.
- Regresion cuantilica.
- Arbol de regresion.
- Modelos de prediccion o score con parametros estimados.
- Modelos de segmentacion o rating con reglas estadisticas sustentadas.

La revision debe verificar que los supuestos, parametros y metricas correspondan al tipo de modelo usado.

## Relacion con METOD7

METOD5 no debe duplicar la evaluacion final de calibracion, discriminacion, distribucion o interpretabilidad del modelo final que corresponde a METOD7.

La diferencia practica es:

- METOD5 revisa si la construccion, muestras, tuneo y seleccion del modelo fueron metodologicamente solidas.
- METOD7 revisa el comportamiento final del modelo ya seleccionado, incluyendo discriminacion, calibracion final, concentracion, distribucion, sensibilidad e interpretabilidad.

En METOD5, la calibracion se usa como criterio de estabilidad durante modelamiento o tuneo. En METOD7, la calibracion se evalua como resultado final del modelo.

## Carteras pequenas

Si la cartera no permite alcanzar mas de 1000 observaciones o mas de 450 eventos target, no se debe marcar incumplimiento automatico.

En ese caso, la revision debe exigir:

- Justificacion de la limitacion de cartera.
- Discusion de la razonabilidad de crear el modelo.
- Evaluacion de tratamiento alternativo, como pauta para la poblacion.
- Evidencia de mitigantes o monitoreo reforzado.

## Informacion fuera de alcance

METOD5 no debe usarse para:

- Definir el contexto especifico del modelo, como nombre, tier, producto, target o variables operativas. Esa informacion viene por widgets.
- Evaluar por completo la implementacion productiva de variables, salvo que afecte la construccion o muestra del modelo.
- Resolver discrepancias de glossary o definiciones internas si no impactan la aceptacion metodologica.
- Reemplazar reglas especificas de otros METOD cuando el hallazgo pertenezca claramente a target, segmentacion, modelo final, backtesting u OOT.
