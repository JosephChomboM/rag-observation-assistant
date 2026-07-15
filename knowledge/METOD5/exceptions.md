# METOD5 - Excepciones y justificaciones aceptables

## Principio general

Una excepcion en METOD5 no elimina el control. Solo permite aceptar una desviacion cuando existe justificacion metodologica, evidencia de impacto limitado y una accion compensatoria razonable.

Toda excepcion debe indicar:

- Responsable o area que sustenta la excepcion.
- Motivo metodologico o de negocio.
- Evidencia que respalda la excepcion.
- Impacto esperado en la validacion.
- Accion de regularizacion, mitigacion o monitoreo.

## Carteras con baja materialidad

Si la cartera no permite superar 1000 observaciones o 450 casos target, la excepcion puede ser aceptable si el informe:

- Explica por que la cartera tiene baja materialidad.
- Discute la razonabilidad de crear el modelo.
- Evalua tratamiento por pauta para la poblacion.
- Indica limitaciones de interpretacion de metricas.
- Propone monitoreo reforzado o revision posterior.

No es aceptable omitir los conteos de muestra y target solo porque la cartera es pequena.

## Ajuste de moras tempranas

Si no aplica ajuste de moras tempranas, el informe debe decirlo explicitamente.

Si aplica, pero se usa una metodologia distinta a la estandar, la excepcion debe justificar:

- Por que la metodologia alternativa es coherente.
- Que ventanas se usaron.
- Por que las ventanas no generan sesgo.
- Como se verifica que el ajuste mejora o estabiliza la medicion.

## Tuneo ML no aplicable

Si el modelo no es ML o no tiene una etapa de tuneo, no se debe exigir la evaluacion de 50 combinaciones de hiperparametros.

En ese caso, la revision debe trasladarse a:

- Supuestos estadisticos.
- Parametros estimados.
- Parametrizacion del modelo.
- Metrica de bondad de ajuste.
- Nivel de aceptacion usado.

## Seleccion por criterio de negocio

Si la seleccion del modelo, variables o parametros depende de un criterio de negocio, la excepcion puede ser aceptable solo si existe evidencia formal.

Evidencia esperada:

- Acta de decision.
- Justificacion en el manual metodologico.
- Comunicacion formal del equipo modelador o area responsable.
- Sustento de que el criterio no invalida la estabilidad o bondad de ajuste.

No es suficiente afirmar que la seleccion fue de negocio sin documentar el motivo y su impacto.

## Modelos tradicionales con controles no aplicables

Algunos supuestos o metricas pueden no aplicar segun el tipo de modelo tradicional.

Ejemplos:

- Supuestos de regresion lineal no aplican igual a un arbol de regresion.
- Una metrica de error puede ser mas relevante que Gini para ciertos estimadores.
- Un modelo de segmentacion puede requerir otro criterio de ajuste.

La excepcion es aceptable si el informe explica por que el control no aplica y cual es el criterio alternativo usado.

## Cuando la excepcion debe generar observacion

La excepcion debe generar observacion si:

- No tiene evidencia.
- No identifica impacto.
- No tiene responsable.
- Cambia la seleccion del modelo y no se sustenta.
- Permite usar Test/OOT en entrenamiento o validacion.
- Omite por completo la metrica de bondad de ajuste.
- Impide concluir si el modelo fue construido con base estadistica suficiente.
