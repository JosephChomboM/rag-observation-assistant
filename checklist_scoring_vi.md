# Checklist Scoring VI - versión LLM-friendly

Este archivo fue convertido desde el Excel original `Checklist Scoring VI.xlsx` a un formato textual estructurado para que Claude, Codex u otro LLM lo pueda leer sin depender del formato de celdas.

## Cómo leer este documento

Cada hoja del Excel se transformó en una sección.  
Cada criterio conserva:
- `fila_excel`: fila original aproximada en el Excel.
- `bloque`: tema o subtema asociado.
- `criterio`: control, validación o revisión que se debe realizar.

## Interpretación general

El contenido corresponde a un checklist metodológico para validar modelos de riesgo crediticio, scoring, PD o modelos relacionados. Cubre datos base, target, segmentación, selección de variables, modelamiento, validación final y backtesting/OOT.

## Índice de hojas

| Hoja | Rango original | Nº criterios | Tema aproximado |
|---|---:|---:|---|
| BBDD 1 | A1:B40 | 25 | Base de datos inicial, universo, target y filtros |
| BBDD 2 | A1:B28 | 21 | Variables finales y master table |
| METOD 1 | A1:B10 | 8 | Validación de población/universo |
| METOD 2 | A1:B16 | 11 | Definición y estabilidad del target |
| METOD 3 | A1:B12 | 9 | Segmentación |
| METOD 4 | A1:B31 | 22 | Selección, tratamiento y transformación de variables |
| METOD 5 | A1:B31 | 24 | Bondad de ajuste, muestras y modelamiento |
| METOD 6 | A1:B14 | 10 | Subpoblaciones y drivers de negocio |
| METOD 7 | A1:B47 | 38 | Modelo final, discriminación, calibración, ML e interpretabilidad |
| METOD 8 | A1:B16 | 13 | Backtesting y OOT |

---

## Hoja: BBDD 1

- Rango original: `A1:B40`
- Criterios extraídos: 25
- Tema aproximado: Base de datos inicial, universo, target y filtros


### Réplica del proceso de extracción del universo

- **Fila 3**: Se puede ejecutar sin errores el script de datos correspondiente a la generación del universo
- **Fila 4**: En el proceso de generación del universo, no se encuentran bases intermedias en las cuales exista duplicidad de registros
- **Fila 5**: El universo reejecutado coincide al 99% con el universo usado en la modelación. En caso se tenga una coincidencia menor, se evalúa la criticidad de la observación en base al impacto en GINI del modelo, signo esperado, significancia y supuestos de selección (correlación, missing, GINI individual, etc) de las variables finalistas.

### Reconstrucción del proceso de extracción del universo

- **Fila 7**: Usando la guía del manual metodológico o un script comentado, se puede construir sin problemas de procesamiento, el universo
- **Fila 8**: El universo reconstruido coincide al 99% con el universo usado en la modelación. En caso se tenga una coincidencia menor, se evalúa la criticidad de la observación en base al impacto en GINI del modelo, signo esperado, significancia y supuestos de selección (correlación, missing, GINI individual, etc) de las variables finalistas.

### Validación de la distribución del universo

- **Fila 10**: No existe tendencia en el volumen mensual de cuentas / saldo que conforman el universo, y de existirlo está justificado por modelamiento y/o el área usuaria
- **Fila 11**: No existen picos atípicos en la población que conforma parte del universo (+- 2 Dev. Est. del volumen mensual), y de existirlo está justificado por modelamiento y/o el área usuaria

### Replica del proceso de extracción del target

- **Fila 13**: Se puede ejecutar sin errores el script de datos correspondiente a la generación del target.
- **Fila 14**: El target reejecutado coincide al 99% con el target usado en la modelación. En caso se tenga una coincidencia menor, se evalúa la criticidad de la observación en base al impacto en GINI del modelo, signo esperado, significancia y supuestos de selección (correlación, missing, GINI individual, etc) de las variables finalistas.

### Reconstrucción del proceso de extracción del target

- **Fila 16**: Usando la guía del manual metodológico o un script comentado, se puede construir sin problemas de procesamiento, el target
- **Fila 17**: El target replicado coincide al 99% con el target usado en la modelación. En caso se tenga una coincidencia menor, se evalúa la criticidad de la observación en base al impacto en GINI del modelo, signo esperado, significancia y supuestos de selección (correlación, missing, GINI individual, etc) de las variables finalistas.

### Validación de la distribución del target

- **Fila 19**: La distribución mensual de cuentas marcadas como target/no target se mantiene sin tendencia, y de no serlo está justificado con el equipo de modelamiento o el área usuaria.
- **Fila 21**: Nota: Para el caso de modelos TIER III, en caso se observen tendencias atípicas en el comportamiento del target que no sean justificables, se procederá con la reconstrucción al 100% del mismo
- **Fila 22**: No existen meses donde la distribución mensual del target/no target sea atípica (PSI>=10% respecto a los meses previos), y de existirlo está justificado por el equipo de modelamiento o el área usuaria.
- **Fila 24**: Nota: Para el caso de modelos TIER III, en caso se observen variaciones atípicas en el comportamiento del target que no sean justificables, se procederá con la reconstrucción al 100% del mismo

### Réplica del proceso de extracción de las variables de filtro

- **Fila 26**: Se puede ejecutar sin errores el script de datos correspondiente a la generación de los filtros
- **Fila 27**: Las variables de filtro reejecutadas, coincide al 99% con las variables filtro usadas en la modelación. En caso se tenga una coincidencia menor, se evalúa la criticidad de la observación en base al impacto en GINI del modelo, signo esperado, significancia y supuestos de selección (correlación, missing, GINI individual, etc) de las variables finalistas.

### Reconstrucción del proceso de extracción de las variables de filtro

- **Fila 29**: Usando la guía del manual metodológico o un script comentado, se pueden construir sin problemas de procesamiento, las variables filtro
- **Fila 30**: Las variables de filtro replicadas, coincide al 99% con las variables filtro usadas en la modelación. En caso se tenga una coincidencia menor, se evalúa la criticidad de la observación en base al impacto en GINI del modelo, signo esperado, significancia y supuestos de selección (correlación, missing, GINI individual, etc) de las variables finalistas.

### Validación de la distribución de las variables de filtro

- **Fila 32**: El porcentaje de missing de las variables filtro se mantiene estable en el tiempo, y de no serlo, tienen justificación del equipo de modelamiento o el área usuaria

### Réplica del proceso de extracción de las variables de segmentación

- **Fila 34**: Se puede ejecutar sin errores el script de datos correspondiente a la generación de las variables de segmentación
- **Fila 35**: Las variables de segmentación reejecutadas, coincide al 99% con las variables de segmentación usadas en la modelación. En caso se tenga una coincidencia menor, se evalúa la criticidad de la observación en base al impacto en GINI del modelo, signo esperado, significancia y supuestos de selección (correlación, missing, GINI individual, etc) de las variables finalistas.

### Reconstrucción del proceso de extracción de las variables de segmentación

- **Fila 37**: Usando la guía del manual metodológico o un script comentado, se pueden construir sin problemas de procesamiento, las variables de segmentación
- **Fila 38**: Las variables de segmentación replicadas, coincide al 99% con las variables de segmentación usadas en la modelación. En caso se tenga una coincidencia menor, se evalúa la criticidad de la observación en base al impacto en GINI del modelo, signo esperado, significancia y supuestos de selección (correlación, missing, GINI individual, etc) de las variables finalistas.

### Validación de la distribución de las variables de segmentación

- **Fila 40**: El porcentaje de missing de las variables de segmentación se mantiene estable en el tiempo, y de no serlo, tienen justificación del equipo de modelamiento o el área usuaria.

---

## Hoja: BBDD 2

- Rango original: `A1:B28`
- Criterios extraídos: 21
- Tema aproximado: Variables finales y master table


### Réplica / Reconstrucción de las variables finales del modelo

- **Fila 4**: I. Para TIER 0, I y II: De acuerdo al control "Réplica / Reconstrucción de las variables finales del modelo", se debe asegurar que se cubra al menos el 75% Tier 0 y I, 50% Tier II del peso de variables para modelos RL, y Gain para modelos ML. Se reconstruyen como máximo:
- **Fila 5**: a. 10 variables para TIER 0.

### > Réplica:

- **Fila 6**: b. 7 variables para TIER I.

### - Se puede ejecutar sin errores el script de datos correspondiente a la generación de las variables finales del modelo (Requisitos: Se cuenta con código de programación comentados (Sql, SAS, R, etc)).

- **Fila 7**: c. 5 variables para tier II.

### > Reconstrucción:

- **Fila 8**: - El resto de variables se replican.

### - Usando la guía del manual metodológico o scripts comentados, se puede construir, sin problemas de procesamiento, las variables finalistas desde las fuentes primarias confiables (Requisitos: se cuenta con un documento de generación de datos y/o definición funcional de variables (descripción, lógica, fuentes, temporalidad).

- **Fila 10**: En caso de modelos ML, el porcentaje de Gain por Tier se coberturará acumulando el top de variables por cada familia, para asegurar que se esté coberturando la diversidad de información del modelo.

### Consideraciones adicionales:

- **Fila 12**: Las fuentes utilizadas para la generación de la información pertenecen a esquemas productivos confiables. En caso no se cuente con una fuente formal (sandbox, datamart, tablas intermedia, información extraída de internet, etc) se debe asegurar que por lo menos cuente con los controles de calidad de datos mínimos (missing y duplicados) y que el equipo de primera línea haya realizado los controles de calidad de datos de su estándar a las variables provenientes de estas fuentes.

### Reconstrucción: Aplica para las variables cuyas fuentes utilizadas por el modelador para extraer la información son confiables (Tablón, ODS, BDS, EDS, HM Seguimiento, etc..)

- **Fila 13**: En el proceso de generación de datos, no se encuentran bases intermedias en las cuales exista duplicidad de registros y que pueda afectar el valor de las variables extraídas.
- **Fila 14**: Todas las variables extraídas coinciden al 99% con las variables extraídas usadas en la modelación (en un intevalo de +- 1% de variación de valores). En caso se tenga una coincidencia menor al 99% en la réplica o reconstrucción, se evalúa la criticidad de esta observación en base al impacto en GINI del modelo, signo esperado, significancia y supuestos de selección (correlación, missing, GINI individual, etc) de las variables finalistas.

### Validación de la distribución de las variables finales del modelo

- **Fila 16**: El porcentaje de missing mensual se mantiene estable en todas las variables
- **Fila 17**: No existen valores missing o ilógicos que vayan contra el sentido común de valores que debe tener la variable
- **Fila 18**: Se analiza la distribución de la variable, la cual debe caer dentro de intervalos lógicos de acuerdo a la naturaleza de la variable
- **Fila 19**: Se analiza la coherencia entre variables finalistas, evaluando que la relación teórica que existe entre dos variables con conceptos similares se mantenga (por ejemplo Deuda Total y Saldo: DT > Saldo y la diferencia entre ambos debe equivaler a intereses y comisiones)
- **Fila 20**: En caso existan variables del modelo que vayan a aproximarse mediante proxys en la implementación, se realizarán todos estos controles de calidad de datos y se verificará que sean satisfactorios.

### Réplica de la master table

- **Fila 22**: Se revisan los filtros previos de la llave primaria, desde la generación de la tabla. Ejemplo: codclavecic != 0
- **Fila 23**: Se revisan los codmes usados en cada tabla, las fechas de actualización de cada tabla (los rezagos), la llave utilizada para los joins y si los joins de las tablas se hacen respetando los rezagos que corresponden. Para el caso de fuentes RCC y BCP, se considera el mejor rezago posible vigente. Caso contrario, se valida un plan con el que tendrán la información con el mejor rezago posible productivizada
- **Fila 24**: Se valida que en los cruces realizados entre las bases inputs de la master table, no se pierde información, y que los cruces realizados son correctos.
- **Fila 25**: Se verifica que las variables finalistas del modelo son todas implementables según su definición funcional.
- **Fila 26**: La master table replicada coincide con la master table usada en la construcción del modelo

### Representatividad muestral para calibrados

- **Fila 27**: Calculo de PSI de las principales variables del modelo (Peso más de 75% Tier I con un máximo de 7 variables) entre la ventana de construcción vs. Población de uso (pasa pauta sin incluir pauta de nivel de score).
- **Fila 28**: Verificar la coherencia en el sentido de la PD por drivers principales del modelo en universo de modelamiento vs universo PEA (post pauta dura)

---

## Hoja: METOD 1

- Rango original: `A1:B10`
- Criterios extraídos: 8
- Tema aproximado: Validación de población/universo


### Universo

- **Fila 3**: En la muestra de validación, se realizó  el análisis de la evolución del volumen mensual de clientes / cuentas totales que comprenden el universo
- **Fila 4**: En la muestra de validación, se realizó el análisis de la evolución del volumen mensual de montos / montos totales que comprenden el universo
- **Fila 5**: En la muestra de validación, se contrastó el volumen mensual de clientes/cuentas que conforman el universo, con los reportes del equipo de negocio (área usuaria) y/o seguimiento
- **Fila 6**: En la muestra de validación, se justifican los picos y valles atípicos que puedan encontrarse al evaluar el volumen mensual de clientes / cuentas / montos

### Clientes de Forzaje (clientes denegados por el modelo, pero que negocio decide darles una excepción en su aprobación)

- **Fila 7**: Se verifica si seguimiento tiene una marca para los desembolsos que entran por forzaje (excepciones). En caso no se tenga, solicitar al equipo usuario la marca que permita identificar a estos clientes.
- **Fila 8**: En los meses de seguimiento del modelo, se realiza un análisis de la evolución del volumen mensual de clientes/cuentas asociados a los clientes de forzaje.
- **Fila 9**: En los meses de seguimiento del modelo, se analiza la estabilidad en distribución (PSI) del volumen mensual de clientes/cuentas asociados a los clientes de forzaje
- **Fila 10**: Se verifica con el equipo usuario si se cuenta con algún umbral de participación mensual de clientes forzados. En caso lo haya, verificar que en los últimos 6 meses no se haya excedido dicho umbral.

---

## Hoja: METOD 2

- Rango original: `A1:B16`
- Criterios extraídos: 11
- Tema aproximado: Definición y estabilidad del target


### Distribución del Target

- **Fila 3**: En la muestra de validación (OOT), se analiza la distribución del target y se compara con la observada en la muestra de entrenamiento
- **Fila 4**: En la muestra de validación (OOT), se analiza el evolutivo mensual del target y se compara con los meses de la muestra de entrenamiento
- **Fila 5**: En la muestra de validación (OOT), se justifican los puntos atípicos en la evolución del target (+- 2 dev.est)
- **Fila 6**: En la muestra de entrenamiento y validación (OOT), se analiza la cartera en default, a través de variables de negocio (DT, ventas, etc)

### Sustento del target

- **Fila 8**: (Control Opcional) Se evalúan definiciones de default alternativo más allá del propio conteo de días de impago. Por ejemplo, definir clientes en default cuando:
- **Fila 9**: - Se tiene información financiera adversa de una empresa (por ejemplo, en un modelo banca negocio se podría incluir una definición de default en base a la información financiera de la empresa en cuestión).
- **Fila 10**: - Desembolsos que, sin haber incumplido ninguna cuota, el cliente al que pertenecen tiene otros desembolsos en mora que suponen más de un 20% del total de deuda con la Entidad.
- **Fila 11**: - El nivel total de apalancamiento del prestatario se ha incrementado de manera significativa o hay expectativas justificadas de que se va a producir dicho aumento de su apalancamiento.
- **Fila 13**: * Si se consigue este default alternativo usando información actual del cliente, este se podría usar como un default de alerta temprana, y permitiría evaluar el performance del modelo en meses recientes.
- **Fila 14**: En la muestra de validación (OOT), se analiza la curva de acumulación del target por cada mes de maduración, y se compara con la evaluada en el entrenamiento del modelo. Se verifica que la maduración seleccionada para el target tenga la suficiente materialidad.

### Distribución del target en clientes de forzaje (clientes denegados por el modelo, pero que negocio decide darles una excepción en su aprobación)

- **Fila 16**: En los meses de seguimiento del modelo, se analiza el evolutivo y estabilidad (PSI) del porcentaje de clientes/cuentas que entraron en default de los clientes de forzaje.  En caso de existir valores atípicos en el porcentaje evaluado, estos deben ser justificados en el análisis.

---

## Hoja: METOD 3

- Rango original: `A1:B12`
- Criterios extraídos: 9
- Tema aproximado: Segmentación


### Segmentación

- **Fila 4**: Se analiza la coincidencia entre el reporte y el sustento enviado al área usuaria.
- **Fila 5**: Se tiene materialidad de los segmentos (mínimo 1000 observaciones por segmento) en caso la cartera lo permita
- **Fila 6**: Se tiene materialidad del target por segmento (mínimo 450 observaciones), en caso la cartera lo permita
- **Fila 7**: Se valida la lógica de construcción de los segmentos
- **Fila 8**: Se valida la estabilidad de las variables de segmentación (PSI<=10% y sin tendencia)
- **Fila 9**: Se valida la estabilidad de los segmentos(PSI<=10% y sin tendencia)
- **Fila 10**: Se realiza el test para probar heterogeneidad entre duplas de segmentos; diferencia de proporciones / diferencia de medias / anova / Kolgomorov Smirnov / Mann.-Whitney-Wilcoxon  - en base al target.
- **Fila 11**: Se realiza el test para probar diferencia entre todos los segmentos (Kruskall-Wallis / Anova) (significativo) -  en base al target.
- **Fila 12**: Se analiza la migración de segmentos de las cuentas / clientes bajo distintas ventanas temporales

---

## Hoja: METOD 4

- Rango original: `A1:B31`
- Criterios extraídos: 22
- Tema aproximado: Selección, tratamiento y transformación de variables


### Análisis Univariado*

- **Fila 3**: Se analiza la tendencia en las variables finalistas (Ratio avg(med.ult.meses)/avg(med.ini.meses)). Se podría usar una desviación +- 2 desv. est. para identificar un comportamiento atípico en las variables.
- **Fila 4**: Se analiza la estabilidad (mensual) de las variables finalistas (PSI<=10%).
- **Fila 5**: Se analiza la estabilidad de missing en las variables finalistas

### Tratamiento de variables (criterio univariado)

- **Fila 7**: El método de imputación usado es coherente con los supuestos y tratamiento de variables del algoritmo de modelación
- **Fila 8**: Se puede reproducir el método de imputación usado para las variables finalistas (%Coincidencia=100%)
- **Fila 9**: Se debe analizar la sensibilidad de la variables * en diferentes escenarios de estrés (Conservador, normal y estresado) para las variables más relevantes (en peso o gain)
- **Fila 10**: Se puede reproducir el método de tratamiento de outliers para las variables finalistas (%Coincidencia = 100%)

### Convolución de variables

- **Fila 12**: Corroborar que las variables convolucionadas tengan sentido / lógica de negocio. Para modelos de Machine Learning verificar el sustento de la inclusión de variables convolucionadas.​

### (Solo en caso se realice este paso)

- **Fila 13**: Para las variables convolucionadas finalistas, reproducir la lógica de convolución (coincidencia 100%)
- **Fila 14**: Medir el aporte de la variable convolucionada finalista en discriminación (respecto a sus inputs delta de gini > 5%)
- **Fila 15**: Medir el aporte de distribución de la variable convolucionada finalista respecto a sus inputs (delta de cobertura > 10%, distribución menos concentrada en valores específicos)

### Análisis de variables - Bivariado

- **Fila 17**: Reproducir los indicadores bivariados de selección para las variables finalistas (coincidencia 100%)

### (GIGO: Garbage in, garbage out)

- **Fila 18**: Validar que la discriminación de las variables finalistas sea estable en el tiempo
- **Fila 19**: En caso de modelos tradicionales, verificar que se cumpla la monotonía de las variales finalistas con el target

### Transformación de variables

- **Fila 21**: Reproducción del método de transformación de variables, en caso este fuera aplicado a alguna variable finalista (coincidencia 100%)

### (Solo en caso se realice este paso)

- **Fila 22**: Validar la estabilidad de la variable finalista transformada
- **Fila 23**: Validar la estabilidad de la discriminación de la variable finalista transformada

### Réplica de selección de variables (solo en caso usen métodos de selección de variables no certificados)

- **Fila 25**: Validar las lógicas del método de selección de variables finalistas. Si es un método basado en reglas dado por el modelador con criterios de negocio, estas deben estar correctamente justificadas y documentadas.
- **Fila 26**: Este control considera:
- **Fila 27**: - Verificar los indicadores obtenidos por metodos/herramientas certificadas. Los indicadores deben ser los mismos a los señalados en el estandar de primera linea.
- **Fila 28**: - En caso el metodo de seleccion de las variables o del mejor modelo se base en criterios de negocio, se requerirá las actas donde se evidencia esta comunicacion y se registre en el manual metodológico.
- **Fila 29**: Reproducción del método de selección de variables finalistas (coincidencia 100% de los indicadores que brinda el método de selección usado)

---

## Hoja: METOD 5

- Rango original: `A1:B31`
- Criterios extraídos: 24
- Tema aproximado: Bondad de ajuste, muestras y modelamiento


### Muestras Train - Dev - Test / Crossvalidation

- **Fila 4**: Validar la suficiencia de observaciones en las muestras Train - Dev - Test (más de 1000 casos en caso la cartera lo permita). En caso la cartera esté por debajo de los 1000 casos, discutir la justificación de creación del modelo y evaluar un tratamiento por pauta para esta población.
- **Fila 5**: Validar la suficiencia de target en las muestras Train - Dev - Test (más de 450 casos en caso la cartera lo permita).  En caso la cartera esté por debajo de los 450 casos, discutir la justificación de creación del modelo y evaluar un tratamiento por pauta para esta población.
- **Fila 6**: Validar la similitud de las muestras Train - Dev - Test usando el target
- **Fila 7**: Validar la similitud de las muestras Train - Dev - Test usando las variables finalistas

### Muestras para modelos ensamblados

- **Fila 9**: Las muestras de entrenamiento / validación de los modelos ensamblados de ML, no deben coincidir con la muestra de Test / OOT usada en la construcción del modelo final

### Ajuste de moras tempranas

- **Fila 11**: Validar que la lógica de la metodología para la obtención de factores sea coherente y con un criterio estándar para todos los modelos.

### (en caso aplique)

- **Fila 12**: Validar que las ventanas seleccionadas para la obtención de los factores sean lógicos y no generen un sesgo en la obtención del factor

### Modelación - Tuneo del modelo ML

- **Fila 14**: Replicar el tuneo del modelo bajo una mayor gama de hiperparámetros (mínimo de 50 combinaciones), para justificar la selección de hiperparámetros

### (De existir más de una etapa de tuneo, se evalúan de la misma forma todas las etapas)

- **Fila 15**: Validar la estabilidad de discriminación (variaciones menores a 5 puntos de GINI de un mes a otro) y calibración del modelo seleccionado por el equipo modelador, respecto al mejor modelo obtenido del tuneo realizado en la validación

### Otros Modelos Tradicionales - Estimadores / Segmentación / Tasaciones / Alertas / Endeudamiento / Rating

- **Fila 17**: Validar que se cumplan los requisitos y supuestos minimos para la aplicación del modelo :
- **Fila 18**: - Regresión lineal (Target, variables y supuestos: normalidad de los residuales (test shapiro wilk), no multicolinealidad (Factor Inflador de Varianza), homocedasticidad de varianzas (test de Barlett o Levene) y no autocorrelación de errores (Test Durbin-Watson)) (* solo se consideraran los analisis para los modelos de prediccion o de score y no sobre transformaciones que puedan emplear dicho proceso/ en el caso de que control no aplique por alguno consideracion metodologica se debera incluir en el informe de validacion dicha justificacion)
- **Fila 19**: - Regresión cuantílica (Target, variables y supuestos: justificación del cuantil óptimo seleccionado)
- **Fila 20**: - Arbol de Regresión (Target, variables y parametrización)
- **Fila 21**: En el caso de Modelos de Regresión evaluar los parametros estimados,  se debe revisar:
- **Fila 22**: - Sentido del beta (económico vs estadístico)
- **Fila 23**: - Peso del beta en el modelo
- **Fila 24**: - Significancia de los betas (p-value)
- **Fila 25**: En el caso de Modelos de Arbol  revisar la parametrización escogida:
- **Fila 26**: - Profundidad del arbol
- **Fila 27**: - Ordenamiento de variables
- **Fila 28**: - Sentido de los nodos
- **Fila 29**: - Materialidad de los nodos
- **Fila 30**: Validar la metrica y el nivel de aceptación que se ha utilizado para evaluar la bondad de ajuste de estos modelos tradicionales:
- **Fila 31**: - R2, Gini,  Entropía,  RECM, Error absoluto,  % aciertos, etc.

---

## Hoja: METOD 6

- Rango original: `A1:B14`
- Criterios extraídos: 10
- Tema aproximado: Subpoblaciones y drivers de negocio


### Análisis del modelo final - Drivers de negocio

- **Fila 4**: Se replica y evalúa la discriminación del modelo en los drivers usados por el equipo modelador y los drivers selecionados por VI en los meses de entrenamiento y OOT
- **Fila 5**: Se evalúa la calibración del modelo en los drivers usados por el equipo modelador y los drivers selecionados por VI en los meses de entrenamiento y OOT
- **Fila 6**: En sombra, se aplican las bandas de volatilidad de VI para reforzar las vistas de calibración de los drivers seleccionados.
- **Fila 7**: Para el caso de un modelo behaviour, se evalúa la vista de calibración por buckets de maduración en los meses de entrenamiento y OOT.
- **Fila 8**: Si en caso el calibrado tenga un ajuste por moras tempranas, verificar que el ajuste ayuda a mejorar la calibración del modelo en meses recientes (proyecciones de RD temprano) en los principales segmentos/drvers del producto.
- **Fila 9**: Se evalua el sentido esperado de la pd respecto a los drivers seleccionados por VI
- **Fila 10**: En caso existan variables del modelo que vayan a aproximarse mediante proxys en la implementación, se deben generar las vistas de calibración en train-dev-test mediante el driver de construcción y el proxy y se debe verificar que en ambas vistas el modelo esté calibrado

### Análisis del modelo final - Drivers Proforma

- **Fila 12**: Inclusión de efecto proforma en los modelos applicant (si no tiene, justificación de limitaciones y/o plan de acción de regularización).
- **Fila 13**: Evaluación de lógicas de variables proforma post desembolso (inclusión línea TC no utilizada en RCC). Validar que en efecto se trabaje con la venta postdesembolso
- **Fila 14**: Análisis de precisión por drivers proforma (monto desembolsado, deuda post-crédito y palanca post-crédito) en train y OOT. En sombra, se calculan las bandas de volatilidad de VI (herramienta propia).

---

## Hoja: METOD 7

- Rango original: `A1:B47`
- Criterios extraídos: 38
- Tema aproximado: Modelo final, discriminación, calibración, ML e interpretabilidad


### Análisis del modelo final - Total - Tradicional

- **Fila 4**: Se puede reproducir el modelo final (discriminación, distribución)

### (En caso de modelos por segmentos o módulos:

- **Fila 5**: Se puede reproducir la significancia de las variables, pesos y sentido de negocio

### > Segmentos - Los modelos por sementos.

- **Fila 6**: Validar que los pesos no estén concentrados más del 25% en una sola variable. En caso se supere este umbral, se evalúa la justificación por parte del equipo de modelamiento.

### > Módulos: Cada modelo de los módulos así como el modelo final deben ser evalaudos)

- **Fila 7**: Validar que los coeficientes de las variables se mantengan en el intervalo del 95% de confianza definido por el análisis boostrapping del modelo en meses de entrenamiento y OOT.
- **Fila 8**: Evaluar la discriminación del modelo (Umbrales de discriminación para el producto / uso y estabilidad de la discriminación). En caso sea una población sesgada, replicar y validar los criterios de definición de este tipo de población.
- **Fila 9**: Evaluar la calibración del modelo. Para ello se debe validar si la población es material en N y default según los criterios definidos por primera línea. En caso sea así, se usarán los límites de Jeffreys para evaluar límites de calibración; caso contrario, se usarán los límites usuales de Vasiceck. Además, se aplicará en sombra las bandas de volatilidad de VI. El criterio para activar una observación de descalibración será:
- **Fila 10**: a) Si la RD sale del límite de aceptable.
- **Fila 11**: b) Si la variación relativa de la PD respecto a la RD > 25%.
- **Fila 12**: c) Se tiene > 30 defaults en el bucket o mes de análisis.
- **Fila 14**: * Si se cumplen estas 3 condiciones, se activará una observación por descalibración considerando el "Estándar de Observaciones - Scores y Parámetros".
- **Fila 15**: Evaluar la distribución del modelo (Histograma de PD que muestre distribución sin concentraciones atípicas ni sesgo) en el periodo de entrenamiento y test
- **Fila 16**: Evaluar la estabilidad de los segmentos de riesgo dados por el modelo (PSI<=10% en todos los meses de Train-Dev-Test)
- **Fila 17**: Para el caso de modelos de admisión (applicant), se realiza un análisis de estabilidad en los últimos 12 meses del ratio [PD BHV (t+1) / PD APP (t)]. Se espera tener PSI <  10% (semáforo verde), en caso el PSI esté entre 10%-25% se activa una alerta ámbar (observación riesgo bajo) y en el caso el PSI > 25% (observación riesgo moderado)
- **Fila 18**: Para el caso de modelos de admisión (applicant), se realiza un análisis de tendencia en los últimos 12 meses del porcentaje de clientes que sobrepasan el umbral del ratio [PD BHV (t+1)/ PD APP (t)] por producto (ver umbrales por producto en hoja de anexo VI - METOD 7). Se debe verificar una estabilidad de este porcentaje.

### Análisis del modelo final - Total - ML

- **Fila 20**: Validar que las principales variables tengan un sentido de negocio coherente con el modelo (Top 20)

### (En caso de modelos por segmentos o módulos:

- **Fila 21**: Validar que no se incluyan variables sin sentido en relación al objetivo del proyecto (relaciones espúreas)

### > Segmentos - Los modelos por sementos.

- **Fila 22**: Validar que los pesos no estén distribuidos más del 10% en una sola variable. En caso se supere este umbral, se evalúa la justificación por parte del equipo de modelamiento.

### > Módulos: Cada modelo de los módulos así como el modelo final deben ser evalaudos)

- **Fila 23**: Validar la estabilidad de los pesos (gain) de las variables mediante bootstrap (los pesos no deben caer fuera del intervalo del 95% de las simulaciones)
- **Fila 24**: Evaluar que el modelo no sea sensible ante hiperparámetros de aleatoriedad, ejecutando modelos bajo los mismos hiperparámetros pero cambiando la semilla aleatoria (intervalo de variación de discriminación <=2%)
- **Fila 25**: Evaluar la parsimonia del modelo, es decir la inclusión de variables que aporten a la discriminación del modelo (Prueba de inclusión de variables al modelo una a una de acuerdo a un criterio de importancia, y evaluando hasta que umbral de variables el modelo sigue mejorando)
- **Fila 26**: Evaluar la discriminación del modelo (Umbrales de discriminación para el producto / uso y estabilidad de la discriminación)
- **Fila 27**: Evaluar la calibración del modelo. Para este caso solo se permitirían los límites de Vasiceck, ya que se supone que la población para un ML tendría suficiente materialidad en N y default. Además, se aplicará en sombra las bandas de volatilidad de VI. El criterio para activar una observación de descalibración sería:
- **Fila 28**: a) Si la RD sale del límite de aceptable.
- **Fila 29**: b) Si la variación relativa de la PD respecto a la RD > 25%.
- **Fila 30**: c) Se tiene > 30 defaults en el bucket o mes de análisis.
- **Fila 32**: * Si se cumplen estas 3 condiciones, se activará una observación por descalibración considerando el "Estándar de Observaciones - Scores y Parámetros".
- **Fila 33**: Evaluar la distribución del modelo (Histograma de PD que muestre distribución sin concentraciones atípicas ni sesgo) en el periodo de entrenamiento y test
- **Fila 34**: Evaluar la estabilidad de los segmentos de riesgo dados por el modelo (PSI<=10% en todos los meses de Train-Dev-Test)
- **Fila 35**: Evaluar y validar el análisis de interpretabilidad de variables del modelo (shap values) de las variables finalistas del modelo. Se verifica que las variables tengan el sentido económico esperado

### Sensibilidad de modelos

- **Fila 37**: Para modelos ML calcular la variación de PD por variaciones de 10%,25% y 50% de las principales variables del modelo (Top 10) para verificar el sentido económico aproximado de cada variable de manera global y por los segmentos principales de interés.

### Sensibilidad del score frente al score macro (para calibrados que presenten componente macro)

- **Fila 39**: Evaluar el impacto en la PD final del componente macro. Para ello se realizan estrés de variación relativas del +- 100% en el score macro y se evalúa la variación porcentual en la PD final del modelo.
- **Fila 40**: Evaluar el impacto en la PD final de las proyecciones de variables macro. Para ello se considera como periodo base los últimos 3 meses de venta con default cerrado y se evalúa el score macro considerando las proyecciones macro de cierre de año. Si este cae fuera de los límites del intervalo de confianza, se genera una observación.
- **Fila 41**: Evaluar si con el score final con el componente macro y basado en las proyecciones de RD de meses más recientes, el score se encuentra calibrado

### Análisis de missing de variables al score troncal

- **Fila 43**: Definir grupos con alta concentración de variables con missing (según peso de variable) por cliente en el score troncal y validar su estabilidad (PSI <= 10%). Usar cortes de >50% y <=50% de missing.
- **Fila 44**: Analizar la distribución de riesgo del score para los grupos con/sin alta concentración de missing.

### *Importante: Se aplica solo si se tiene la macro automatizada con este control

- **Fila 45**: Analizar la discriminación para los segmentos con/sin alta concentración de missing.
- **Fila 46**: Realizar un análisis de estrés agregando missing a las variables finalistas para encontrar un umbral adecuado para definir un cliente con alta concentración de missing.
- **Fila 47**: Se realiza el análisis de estabilidad, distribución del score y discriminación en los grupos con/sin alta concentración de missing para todos los usos directos del modelo base (a nivel producto).

---

## Hoja: METOD 8

- Rango original: `A1:B16`
- Criterios extraídos: 13
- Tema aproximado: Backtesting y OOT


### Backtesting / OOT

- **Fila 4**: Medir la estabilidad de distribución de las variables entre las muestras Train-Dev-Test y Backtesting/OOT  (PSI <=10% en todas las variables / Si es un modelo por segmento, el criterio debe cumplirse a nivel total y a nivel del segmento donde es usada la variable). En caso existan variables del modelo que vayan a aproximarse mediante proxys en la implementación, también se realiza este control a la variable proxy.
- **Fila 5**: Medir gráficamente la estabilidad de distribución de las variables entre las muestras Train-Dev-Test-Backtesting/OOT y reportar la existencia de tendencia o quiebre en las variables (criterio cumplido si no se reportan variables con incidencias)
- **Fila 6**: Comparar la discriminación de las variables entre las muestras Train-Dev-Test y Backtesting/OOT (delta de discriminación en Backtesting/OOT en un intervalo de +-X%  de la discriminación de construcción / Si es un modelo por segmento, el criterio debe cumplirse a nivel total y a nivel del segmento donde es usada la variable)
- **Fila 7**: Medir gráficamente la estabilidad de la discriminación de las variables entre las muestras Train-Dev-Test-Backtesting/OOT y reportar la existencia de tendencia o quiebre en las variables (criterio cumplido si no se reportan variables con incidencias / Si es un modelo por segmento, el criterio debe cumplirse a nivel total y a nivel del segmento donde es usada la variable))
- **Fila 8**: Medir la estabilidad de los segmentos en la base de Backtesting/OOT (PSI<=10%)
- **Fila 9**: Medir gráficamente la estabilidad de la distribución de los segmentos entre las muestras Train-Dev-Test-Backtesting/OOT respecto a la existencia de tendencia o quiebres (criterio cumplido si no se reportan incidencias)
- **Fila 10**: Medir gráficamente la estabilidad del RD de los segmentos entre las muestras Train-Dev-Test-Backtesting/OOT respecto a la existencia de tendencia o quiebres (criterio cumplido si no se reportan incidencias)
- **Fila 11**: Medir la estabilidad de la discriminación del modelo entre las muestras Train-Dev-Test y Backtesting/OOT (delta de discriminación GINI en Backtesting/OOT no mayor a 10% en un modelo ML y 2.5% en un modelo Tradicional respecto a la discriminación de construcción / a nivel del modelo general, segmentos, modulos)
- **Fila 12**: Medir gráficamente la estabilidad evolutiva mensual de la discriminación del modelo entre las muestras Train-Dev-Test-Backtesting/OOT y reportar la existencia de tendencia o quiebre en la discriminación (criterio cumplido si no se reportan incidencias / a nivel total, segmentos, módulos)
- **Fila 13**: Medir la estabilidad de la distribución de segmentos de riesgo (bucket de PD) del modelo entre las muestras Train-Dev-Test y Backtesting/OOT (PSI <=10% a nivel total, segmentos, modulos)
- **Fila 14**: Medir gráficamente la estabilidad del ordenamiento del modelo entre las muestras Train-Dev-Test y Backtesting/OOT (Variación de RD / PD por riesgo <=X%)
- **Fila 15**: Medir la estabilidad global de la calibración del modelo entre las muestras Train-Dev-Test y Backtesting/OOT (Indicador de calibración de Train-Dev-Test similar a Backtesting/OOT --> Diferencia <=X%).
- **Fila 16**: Medir gráficamente la estabilidad evolutiva mensual de la calibración del modelo entre las muestras Train-Dev-Test-Backtesting/OOT y reportar la existencia de tendencia o quiebre en la calibración (criterio cumplido si no se reportan incidencias / a nivel total, segmentos, módulos)
