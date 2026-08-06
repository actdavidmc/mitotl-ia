# Nomenclaturas

## Niveles de prioridad


| Nivel             | Significado                                                |
| ----------------- | ---------------------------------------------------------- |
| IMPRESCINDIBLE    | Necesario para que el MVP cumpla su propósito.             |
| IDEAL             | Aporta mucho valor, pero el MVP puede entregarse sin ello. |
| OPCIONAL          | Mejora la experiencia, pero no es prioritario.             |
| OMITIBLE          | Puede descartarse sin afectar el objetivo principal.       |
| FUTURAS_VERSIONES | Funcionalidad posterior al MVP.                            |




## Estados de avance


| Estado        | Significado                                                           |
| ------------- | --------------------------------------------------------------------- |
| PENDIENTE     | No existe evidencia de implementación ni de avance técnico verificable en el repositorio. |
| DOCUMENTADO   | La decisión o definición está registrada, pero no existe validación de usuario o técnica. Se usa para distinguir alcance documentado de funcionalidad pendiente. |
| EN_DESARROLLO | Existe código o trabajo parcial, pero aún no está completo.          |
| IMPLEMENTADO  | La funcionalidad integrada existe en el proyecto.                    |
| VALIDADO      | Está implementada y cuenta con prueba, demo o artefacto verificable. |




## Estados de implementación

| Estado | Significado |
| --- | --- |
| ⚪ No iniciado | No existe implementación verificable en el repositorio. |
| 📄 Documentado | Existe una definición o decisión registrada, sin validación adicional. |
| 🟡 En desarrollo | Existe una implementación parcial o no integrada por completo. |
| 🔵 Implementado | La funcionalidad está integrada en el código del proyecto. |
| ✅ Validado | La funcionalidad está implementada y respaldada por pruebas, demos o artefactos verificables. |


# Diseño de Solución

## Etapa 0 — Identidad del proyecto

| Etapa | Rubro | Subrubro | Descripción | Entregable / evidencia | Nivel de Prioridad | Estado de avance | Estado de implementación |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0-Identidad del proyecto | Nombre Compañía |  | Mitotl IA | Nombre registrado en la estrategia del proyecto. | IMPRESCINDIBLE | DOCUMENTADO | 📄 Documentado |
| 0-Identidad del proyecto | Logo Compañía |  | Mitotl IA | Logo integrado o referencia visual documentada. | IDEAL | VALIDADO | ✅ Validado |

## Etapa 1 — Planteamiento del Problema

| Etapa | Rubro | Subrubro | Descripción | Entregable / evidencia | Nivel de Prioridad | Estado de avance | Estado de implementación |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1-Planteamiento del Problema | Nicho de Negocio |  | Aprendizaje autónomo en clases de danza mediante videos de referencia, para identificar pasos o momentos específicos que pueden mejorar, sin evaluar si la persona baila bien o mal. | Descripción del nicho documentada. | IMPRESCINDIBLE | DOCUMENTADO | 📄 Documentado |
| 1-Planteamiento del Problema | Usuario Final |  | Personas que desean recibir retroalimentación sobre sus coreografías practicadas a solas, especialmente quienes hacen trends en TikTok o están aprendiendo con un video de referencia de un ejercicio o coreografía. | Perfil de usuario documentado. | IMPRESCINDIBLE | DOCUMENTADO | 📄 Documentado |
| 1-Planteamiento del Problema | Problema |  | La persona puede tener dificultades para practicar si no cuenta con espejos, instalaciones adecuadas o videos de referencia. Incluso cuando ya conoce la coreografía, puede no identificar qué está fallando ni cómo mejorar. | Problema documentado y delimitado. | IMPRESCINDIBLE | DOCUMENTADO | 📄 Documentado |
| 1-Planteamiento del Problema | Necesidad |  | La persona necesita identificar momentos específicos de dificultad, partes del cuerpo por corregir, explicaciones claras y una guía para practicar. | Necesidad documentada; confirmación con usuarios pendiente. | IMPRESCINDIBLE | DOCUMENTADO | 📄 Documentado |
| 1-Planteamiento del Problema | Propuesta de valor |  | Mitotl IA proporciona retroalimentación concreta sobre una coreografía y un agente conversacional básico que ayuda a interpretar el resultado y mejorar. El coaching personalizado, el seguimiento de progreso y los planes de práctica quedan para versiones avanzadas. | Propuesta de valor documentada y alcance básico/avanzado diferenciado. | IMPRESCINDIBLE | DOCUMENTADO | 📄 Documentado |
| 1-Planteamiento del Problema | Caso de uso principal |  | La persona sube un video de referencia y un video de ejecución, recibe un análisis comparativo con áreas de mejora y puede consultar al agente de IA sobre su desempeño o sobre una duda de danza. La captura mediante cámara queda como función ideal. | Flujo principal implementado y demostrado con videos cargados; flujo de cámara pendiente. | IMPRESCINDIBLE | IMPLEMENTADO | 🔵 Implementado |

## Etapa 2 — Fuente(s) de Datos

| Etapa | Rubro | Subrubro | Descripción | Entregable / evidencia | Nivel de Prioridad | Estado de avance | Estado de implementación |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2-Fuente(s) de Datos | Video de referencia |  | Fuente académica seleccionada para obtener el video de referencia inicial del MVP. Se utilizará una secuencia de danza con una persona, cámara frontal y cuerpo completo visible. El video se empleará para probar la extracción de pose, la comparación corporal y el pipeline inicial. AIST Dance Database es la fuente principal de video del MVP y su uso está sujeto a sus condiciones académicas y términos de uso. El archivo local no debe redistribuirse. La copia idéntica como ejecución solamente sirve como prueba de humo y no representa una evaluación real de calidad de danza. Más adelante será necesario incorporar ejecuciones distintas realizadas por usuarios o videos con permisos compatibles. AIST no se utilizará como conjunto etiquetado para entrenar un modelo de calidad de danza, porque no contiene etiquetas de errores o desempeño correcto/incorrecto. | Enlace: https://aistdancedb.ongaaccel.jp/. Licencia o términos de uso, metadatos del video, archivo local ignorado por Git y registro en `data/metadata/reference_video_inventory.csv`. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 2-Fuente(s) de Datos | Anotaciones y movimiento | AIST++ | Fuente complementaria documentada para una posible validación técnica de anotaciones 2D, landmarks, confianza y cobertura corporal. No es la fuente principal de videos RGB ni forma parte del flujo mínimo del MVP; la descarga de sus anotaciones queda pendiente. | Información académica y decisión documentada en el notebook 01; las anotaciones no están descargadas ni integradas. | IDEAL | DOCUMENTADO | 📄 Documentado |
| 2-Fuente(s) de Datos | Video de referencia |  | Video de referencia alternativo cargado por la persona usuaria para aprender o imitar un movimiento. La aplicación permite cargarlo, pero no verifica automáticamente autorización, licencia o procedencia. | Componente de carga de referencia propia funcionando; registro de procedencia y permisos queda bajo responsabilidad de la persona usuaria. | IDEAL | IMPLEMENTADO | 🔵 Implementado |
| 2-Fuente(s) de Datos | Video de ejecución |  | La carga del video de ejecución forma parte del MVP. La grabación mediante cámara y el análisis posterior se reservan como función ideal. La política de conservación o eliminación automática todavía está en discusión. | Video de ejecución cargado y analizado; flujo de cámara y política de conservación/eliminación pendientes. | IMPRESCINDIBLE | IMPLEMENTADO | 🔵 Implementado |
| 2-Fuente(s) de Datos | Cámara |  | La captura mediante cámara está definida como una función ideal del MVP para grabar una sesión de práctica y analizarla después. No necesita entregar feedback perfectamente en tiempo real; esa función queda como ideal. La política de conservación o eliminación automática todavía está en discusión. | No existe implementación de captura mediante cámara; la decisión de incluirla como función ideal está documentada y la política de conservación/eliminación queda pendiente. | IDEAL | PENDIENTE | ⚪ No iniciado |
| 2-Fuente(s) de Datos | Fuente externa futura |  | Posible fuente futura de videos de referencia. Su incorporación dependerá de permisos, licencia, disponibilidad técnica, restricciones de descarga y no redistribución del contenido. No forma parte de las fuentes confirmadas del MVP. | No existe una fuente adicional integrada ni una evaluación técnica concluida. | FUTURAS_VERSIONES | PENDIENTE | ⚪ No iniciado |
| 2-Fuente(s) de Datos | Fuente externa futura |  | Posible fuente futura de movimiento 3D y no fuente principal de video RGB. Su uso deberá definirse por separado de las fuentes de referencia visual del MVP. | No existe una fuente 3D integrada ni una evaluación técnica concluida. | FUTURAS_VERSIONES | PENDIENTE | ⚪ No iniciado |
| 2-Fuente(s) de Datos | Datos derivados |  | Resultados derivados del procesamiento de los videos: landmarks corporales, coordenadas normalizadas, ángulos articulares, trayectorias, marcas de tiempo, visibilidad, segmentos, diferencias y puntuaciones. No son fuentes externas; son resultados generados por Mitotl IA. La función inicial de Mitotl IA será una similitud basada en variables corporales, DTW y reglas ponderadas. | Esquema o tabla de datos derivados documentado. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |

## Etapa 3 — EDA, Visualización

| Etapa | Rubro | Subrubro | Descripción | Entregable / evidencia | Nivel de Prioridad | Estado de avance | Estado de implementación |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3-EDA, Visualización | Calidad del video |  | Revisión de la duración, cantidad de cuadros por segundo y resolución de los videos de referencia y ejecución para determinar si tienen condiciones adecuadas para el análisis. | Tabla de calidad de referencia, validación de entradas en el pipeline y artefactos locales de referencia y ejecución. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 3-EDA, Visualización | Detección corporal |  | El MVP se limita a una persona con el cuerpo completo visible. Se revisan los landmarks detectados y la visibilidad de cada punto corporal. | Tabla de calidad de landmarks de referencia y artefactos locales de pose para referencia y ejecución. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 3-EDA, Visualización | Detección corporal |  | Detección y manejo de más de una persona dentro del video. Esta capacidad queda reservada para una versión futura. | Prueba o diseño de detección de varias personas. | FUTURAS_VERSIONES | PENDIENTE | ⚪ No iniciado |
| 3-EDA, Visualización | Visualización de landmarks |  | Representación de los landmarks corporales sobre el video o sobre imágenes de momentos seleccionados para inspeccionar la detección del movimiento. | Imagen o video con landmarks superpuestos y registro de la revisión. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 3-EDA, Visualización | Comparación de poses |  | Contraste visual entre la pose del video de referencia y la pose del video de ejecución en momentos clave de la coreografía. | Gráfica o imagen comparativa de poses en momentos clave. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 3-EDA, Visualización | Trayectoria de articulaciones |  | Representación del recorrido de manos, brazos, piernas u otras articulaciones a lo largo de la ejecución y su comparación con la referencia. | Gráfica de trayectorias articulares por segmento o momento clave. | IDEAL | VALIDADO | ✅ Validado |
| 3-EDA, Visualización | Zonas de diferencia |  | Señalamiento visual de las partes del cuerpo con mayor desviación respecto al video de referencia. | Imagen, video o mapa corporal con zonas de diferencia destacadas. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 3-EDA, Visualización | Tablas |  | Tabla de análisis por momento clave: tiempo, paso o movimiento esperado, parte del cuerpo involucrada, diferencia detectada y recomendación de mejora. | Tabla de hallazgos con momentos, movimientos esperados, partes del cuerpo, diferencias y recomendaciones. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 3-EDA, Visualización | Gráficas |  | Comparación visual de poses entre el video de referencia y el de ejecución, trayectoria de articulaciones y zonas de diferencia en el cuerpo, enfocadas en momentos o segmentos clave de la coreografía. | Conjunto de gráficas ejecutadas para documentar el análisis. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 3-EDA, Visualización | KPIs |  | Porcentaje de coincidencia y similitud por parte del cuerpo de la sesión actual; la similitud temporal se muestra en la sección de sincronización y los hallazgos se presentan en una tabla separada. El avance entre sesiones queda como funcionalidad futura al requerir historial de prácticas. | Panel de score y similitudes corporales, tabla de sincronización temporal y tabla de hallazgos de la sesión analizada. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |

## Etapa 4 — Ingeniería de variables

| Etapa | Rubro | Subrubro | Descripción | Entregable / evidencia | Nivel de Prioridad | Estado de avance | Estado de implementación |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 4-Ingeniería de variables | Fase 1 |  | Extracción de variables base de los videos cargados: puntos de articulación, coordenadas, ángulos, marcas de tiempo, velocidad de movimiento y normalización. La cámara en vivo queda como función ideal. Como posibles variables futuras: orientación general del cuerpo y nivel de confianza de la detección. | Conjunto de variables base documentado mediante sus subrubros y artefactos locales; captura en vivo no forma parte del flujo implementado. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 4-Ingeniería de variables | Fase 1 |  | Posición de cada landmark corporal a lo largo del video de referencia y del video de ejecución. | Tabla o archivo de coordenadas corporales extraídas. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 4-Ingeniería de variables | Fase 1 |  | Relaciones angulares entre articulaciones para describir la postura y el movimiento corporal. | Tabla o archivo de ángulos articulares calculados. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 4-Ingeniería de variables | Fase 1 |  | Nivel de visibilidad o confianza de cada landmark detectado para identificar puntos corporales poco confiables. | Tabla o archivo de visibilidad asociado a los landmarks. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 4-Ingeniería de variables | Fase 1 |  | Transformación de las coordenadas para hacer comparables los movimientos aunque cambie la distancia, escala o posición de la persona frente a la cámara. | Tabla o archivo de coordenadas normalizadas y criterio de transformación documentado. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 4-Ingeniería de variables | Fase 1 |  | Asociación de cada variable corporal con su instante correspondiente dentro del video. | Tabla o archivo de variables con marcas de tiempo. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 4-Ingeniería de variables | Fase 1 |  | Medición del cambio de posición de las articulaciones a lo largo del tiempo. | Tabla o archivo de velocidades articulares calculadas. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 4-Ingeniería de variables | Fase 2 |  | Cálculo de variables derivadas: similitud entre poses, diferencia de ángulos, desplazamiento de articulaciones, sincronización temporal y detección de momentos clave. Como posibles variables futuras: sincronización con el ritmo, suavidad del movimiento y consistencia entre repeticiones. | Conjunto de variables derivadas documentado mediante sus subrubros. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 4-Ingeniería de variables | Fase 2 |  | Diferencia de posición de las articulaciones entre momentos correspondientes de la referencia y la ejecución. | Tabla o archivo de desplazamientos articulares calculados. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 4-Ingeniería de variables | Fase 2 |  | Grado de coincidencia entre la pose del video de referencia y la pose del video de ejecución. | Tabla o archivo de valores de similitud por momento o segmento. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 4-Ingeniería de variables | Fase 2 |  | Desviación angular entre las articulaciones correspondientes de la referencia y la ejecución. | Tabla o archivo de diferencias angulares por articulación. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 4-Ingeniería de variables | Fase 2 |  | Alineación de momentos equivalentes entre el video de referencia y el video de ejecución para compararlos correctamente. | Archivo o tabla con la alineación temporal entre ambos videos. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 4-Ingeniería de variables | Fase 2 |  | División de la coreografía en partes o ventanas comparables para analizar movimientos específicos. | Segmentos identificados y registrados por rango de tiempo. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 4-Ingeniería de variables | Fase 2 |  | Identificación de instantes relevantes de la coreografía para generar hallazgos y retroalimentación. | Lista o tabla de momentos clave con sus marcas de tiempo. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 4-Ingeniería de variables | Fase 2 |  | Relación entre los movimientos corporales y el ritmo o la música de la coreografía. | Análisis documentado de sincronización entre movimiento y ritmo. | FUTURAS_VERSIONES | PENDIENTE | ⚪ No iniciado |
| 4-Ingeniería de variables | Fase 2 |  | Medición de la continuidad del movimiento y de la presencia de cambios bruscos durante la ejecución. | Métrica o visualización de suavidad del movimiento. | FUTURAS_VERSIONES | PENDIENTE | ⚪ No iniciado |
| 4-Ingeniería de variables | Fase 2 |  | Comparación de varias ejecuciones para medir la estabilidad del desempeño de la persona usuaria. | Comparación documentada entre repeticiones. | FUTURAS_VERSIONES | PENDIENTE | ⚪ No iniciado |
| 4-Ingeniería de variables | Fase 3 |  | Preparación de variables para el análisis principal: sincronización y segmentación de los videos, normalización de coordenadas, transformación de diferencias en indicadores comprensibles y validación de la calidad de captura. Estas variables pueden utilizarse para feedback visual en tiempo real, clasificado como ideal, y alimentarán al agente de IA. | Resultados preparados para visualización y agente mediante sus subrubros. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 4-Ingeniería de variables | Fase 3 |  | Transformación de las desviaciones corporales en valores comprensibles para interpretar el resultado del análisis. | Tabla o archivo de indicadores de diferencia por momento y parte del cuerpo. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 4-Ingeniería de variables | Fase 3 |  | Detección de videos incompletos, mala visibilidad o cantidad insuficiente de landmarks para producir un análisis confiable. | Reporte de validación con errores, advertencias y resultado de calidad. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 4-Ingeniería de variables | Fase 3 |  | Organización de los resultados para alimentar la visualización y el agente de IA. | Estructura de resultados lista para visualización y contexto del agente. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |

## Etapa 5 — Modelación

| Etapa | Rubro | Subrubro | Descripción | Entregable / evidencia | Nivel de Prioridad | Estado de avance | Estado de implementación |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 5-Modelación |  |  | En el MVP se utilizará un enfoque híbrido basado en un modelo preentrenado de estimación de pose, comparación geométrica de coordenadas y ángulos, alineación temporal mediante DTW y reglas con umbrales para generar alertas y recomendaciones. Para futuras versiones se consideran modelos temporales como LSTM, TCN o Transformers, modelos especializados en movimiento corporal y personalización por usuario. | Estrategia de modelación, resultados de evaluación y prueba de humo documentados mediante sus subrubros. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 5-Modelación | Extracción de pose |  | Uso de un modelo preentrenado para obtener landmarks corporales a partir del video de referencia y del video de ejecución. | Resultado de extracción de pose sobre los videos de prueba. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 5-Modelación | Similitud corporal |  | Comparación de poses, coordenadas, ángulos y desplazamientos para estimar el grado de coincidencia corporal. | Resultado de similitud por momento, segmento y parte del cuerpo. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 5-Modelación | Sincronización temporal / DTW |  | Alineación de las secuencias de referencia y ejecución mediante DTW para comparar movimientos realizados a diferentes velocidades. | Matriz o resultado de alineación temporal entre ambas secuencias. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 5-Modelación | Puntuación general |  | Score final = 80% similitud corporal + 20% similitud temporal. La escala será de 0 a 100 y representa una estimación orientativa para apoyar la práctica, no una evaluación profesional de calidad de danza. | Fórmula, escala y cálculo del score final documentados. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 5-Modelación | Puntuación por parte del cuerpo |  | Cálculo de resultados diferenciados para brazos, piernas, torso, cabeza u otras partes corporales. | Similitudes desglosadas por parte del cuerpo. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 5-Modelación | Puntuación temporal |  | Resultado de la alineación temporal y de la coincidencia del movimiento a lo largo de la secuencia. | Similitud temporal calculada y registrada. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 5-Modelación | Reglas de feedback |  | Conversión de las diferencias detectadas en recomendaciones concretas de mejora. | Catálogo de reglas y ejemplos de recomendaciones generadas. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 5-Modelación | Evaluación |  | Verificación de que los landmarks corporales se detecten correctamente en los videos de prueba. | Reporte de revisión de landmarks detectados. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 5-Modelación | Evaluación |  | Revisión técnica preliminar de que las puntuaciones reflejen las diferencias observables entre la referencia y la ejecución. | Comparación documentada entre resultados y diferencias observables; la evaluación de calidad de danza con usuarios queda pendiente. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 5-Modelación | Evaluación |  | Comprobación del funcionamiento del pipeline completo utilizando AIST y una copia temporal de ejecución. Esta prueba técnica no representa una evaluación real de calidad de danza. | Resultado de prueba de humo documentado y aclaración de sus limitaciones. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |

## Etapa 6 — Pipeline/Inferencia

| Etapa | Rubro | Subrubro | Descripción | Entregable / evidencia | Nivel de Prioridad | Estado de avance | Estado de implementación |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 6-Pipeline/Inferencia | [Ir al Diagrama](#Diagrama-Pipeline) |  |  | Diagrama Mermaid actualizado y flujo documentado mediante sus subrubros. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 6-Pipeline/Inferencia | Carga |  | Recepción del video de referencia y del video de ejecución cargado por la persona usuaria. | Prueba de carga de ambos videos y registro de entradas recibidas. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 6-Pipeline/Inferencia | Validación |  | Revisión del formato, calidad, duración y condiciones mínimas de los videos antes de iniciar el análisis. | Reporte de validación de entradas con errores y advertencias. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 6-Pipeline/Inferencia | Extracción |  | Obtención de frames, landmarks y variables corporales a partir de los videos validados. | Resultado de extracción de frames, landmarks y variables. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 6-Pipeline/Inferencia | Sincronización y segmentación |  | Alineación temporal y división de los videos en momentos o ventanas comparables. | Segmentos alineados y registrados por rango de tiempo. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 6-Pipeline/Inferencia | Comparación |  | Comparación de la postura, los ángulos, las trayectorias y el movimiento entre la referencia y la ejecución. | Resultado comparativo por momento, segmento y parte del cuerpo. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 6-Pipeline/Inferencia | Cálculo del score |  | Cálculo del score general y de resultados desglosados por momento, segmento y parte del cuerpo. | Score calculado y registrado para la sesión analizada. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 6-Pipeline/Inferencia | Segmentos débiles |  | Identificación de los momentos o segmentos en los que la ejecución presenta mayor diferencia respecto a la referencia. | Lista de segmentos débiles ordenados por nivel de desviación. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 6-Pipeline/Inferencia | Visualización de resultados |  | Presentación de scores, diferencias, poses comparadas y zonas del cuerpo que requieren atención. | Captura o demo de la visualización de resultados. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 6-Pipeline/Inferencia | Retroalimentación |  | Transformación de los hallazgos del análisis en recomendaciones específicas para mejorar la ejecución. | Ejemplos de retroalimentación generada a partir de hallazgos. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 6-Pipeline/Inferencia | Modo grabado |  | Procesamiento de un video de referencia y un video de ejecución previamente cargados. Es el modo principal del MVP. | Demo funcional del análisis con videos cargados. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 6-Pipeline/Inferencia | Modo cámara |  | Grabación de una sesión de práctica mediante la cámara y análisis posterior del video. La cámara es una función ideal para el MVP y no requiere feedback perfectamente en tiempo real. | No existe implementación de captura mediante cámara ni demo de este flujo. | IDEAL | PENDIENTE | ⚪ No iniciado |
| 6-Pipeline/Inferencia | Modo tiempo real |  | Generación de retroalimentación mientras la persona realiza el movimiento frente a la cámara. | No existe implementación de captura ni retroalimentación durante la práctica. | IDEAL | PENDIENTE | ⚪ No iniciado |
| 6-Pipeline/Inferencia | Agente básico |  | Uso del score, segmentos débiles y partes del cuerpo con mayor diferencia para responder preguntas y explicar recomendaciones básicas. Si no existe API key, el flujo de análisis y la alternativa no conversacional deben continuar disponibles. | Integración y demo del agente básico; la continuidad del análisis determinista sin API key está implementada, pero su prueba automatizada específica queda pendiente. | IMPRESCINDIBLE | IMPLEMENTADO | 🔵 Implementado |

## Etapa 7 — Consumo de modelos

| Etapa | Rubro | Subrubro | Descripción | Entregable / evidencia | Nivel de Prioridad | Estado de avance | Estado de implementación |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 7-Consumo de modelos |  |  | MediaPipe será el modelo base del MVP para estimación de pose. Ultralytics queda reservado para futuras versiones. El agente conversacional básico será imprescindible, mientras que sus capacidades avanzadas se manejarán por separado como ideales o futuras. | Uso de modelos y alcance básico/avanzado del agente documentados mediante sus subrubros. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 7-Consumo de modelos | MediaPipe |  | Modelo seleccionado para extraer landmarks corporales del video de referencia AIST y del video de ejecución durante el MVP. | Resultado de extracción de pose con MediaPipe sobre videos de prueba. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 7-Consumo de modelos | Ultralytics |  | Modelo considerado para futuras versiones, como alternativa o ampliación de la estimación de pose del MVP. | Comparación documentada de resultados, compatibilidad y utilidad para una versión futura. | FUTURAS_VERSIONES | PENDIENTE | ⚪ No iniciado |
| 7-Consumo de modelos | Agente conversacional |  | Agente básico en texto que recibe el score, los segmentos débiles y las partes del cuerpo con mayor diferencia; responde preguntas sobre el resultado y explica recomendaciones básicas. Puede funcionar con una API key configurada. | Demo del agente básico con contexto de una sesión analizada y prueba de contrato con cliente simulado. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 7-Consumo de modelos | Agente conversacional |  | El agente recibirá resultados del análisis, scores, segmentos débiles, partes del cuerpo involucradas y recomendaciones para responder de forma contextual. | Ejemplo de contexto estructurado y respuestas del agente basadas en una sesión. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 7-Consumo de modelos | Agente conversacional |  | Manejo controlado de la ausencia de API key mediante un mensaje claro; el análisis determinista y la consulta de resultados permanecen disponibles sin el agente. | Manejo implementado en la interfaz; prueba automatizada específica sin API key pendiente. | IMPRESCINDIBLE | IMPLEMENTADO | 🔵 Implementado |
| 7-Consumo de modelos | Agente conversacional |  | Análisis multimodal de clips, coaching personalizado, seguimiento de progreso, explicación avanzada de conceptos y planes de práctica. | Diseño o prototipo de capacidades avanzadas. | IDEAL | PENDIENTE | ⚪ No iniciado |

## Etapa 8 — Elementos gráficos

| Etapa | Rubro | Subrubro | Descripción | Entregable / evidencia | Nivel de Prioridad | Estado de avance | Estado de implementación |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 8-Elementos gráficos |  |  | Carga del video de referencia y del video de ejecución. Reproductor con comparación de poses y zonas de diferencia, tabla de hallazgos y recomendaciones, indicadores principales, campo de texto para conversar con el agente de IA y controles disponibles para iniciar y consultar el análisis. La cámara, pausa y repetición quedan fuera del flujo actual. | Prototipo funcional y evidencias locales de interfaz; cámara, pausa y repetición quedan fuera del flujo actual. | IMPRESCINDIBLE | IMPLEMENTADO | 🔵 Implementado |
| 8-Elementos gráficos | Identidad visual |  | Elemento visual para identificar Mitotl IA dentro de la aplicación. | Logo integrado en la interfaz. | IDEAL | VALIDADO | ✅ Validado |
| 8-Elementos gráficos | Entrada de referencia |  | Componente para cargar y visualizar el video de referencia seleccionado. | Captura o demo de la tarjeta de referencia funcionando. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 8-Elementos gráficos | Entrada de ejecución |  | Componente para cargar el video de ejecución de la persona usuaria. El acceso a la cámara queda como función ideal. | Captura o demo de la tarjeta de ejecución cargando un archivo. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 8-Elementos gráficos | Cámara |  | Componente ideal para grabar una sesión de práctica y enviarla al análisis posterior. El feedback perfectamente en tiempo real queda como funcionalidad ideal. | No existe componente de cámara ni demo de captura con controles. | IDEAL | PENDIENTE | ⚪ No iniciado |
| 8-Elementos gráficos | Score |  | Visualización del resultado general y de los resultados desglosados por parte del cuerpo. | Captura o demo de scores generales y corporales. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 8-Elementos gráficos | Gráficas |  | Visualización del video comparativo sincronizado, poses y landmarks superpuestos, zonas de diferencia y similitud temporal entre referencia y ejecución. Las trayectorias articulares se mantienen como evidencia exploratoria del EDA. | Capturas y demo de las visualizaciones de la aplicación; trayectorias documentadas en los notebooks exploratorios. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 8-Elementos gráficos | Tabla de hallazgos |  | Presentación tabular de los momentos analizados, las diferencias detectadas y las recomendaciones correspondientes. | Captura o demo de la tabla de hallazgos. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 8-Elementos gráficos | Clips comparativos |  | Presentación de fragmentos de la referencia y la ejecución correspondientes a los segmentos con mayor diferencia. | Demo de clips comparativos de segmentos débiles. | IDEAL | VALIDADO | ✅ Validado |
| 8-Elementos gráficos | Asistente |  | Componente de interfaz para realizar preguntas al agente básico sobre el análisis o sobre dudas específicas de danza. | Captura o demo del asistente básico respondiendo en la interfaz. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 8-Elementos gráficos | Asistente avanzado |  | Interfaz futura para análisis multimodal, coaching personalizado, seguimiento de progreso, explicación avanzada y planes de práctica. | Prototipo o diseño de la interfaz avanzada. | IDEAL | PENDIENTE | ⚪ No iniciado |
| 8-Elementos gráficos | Controles |  | Control para iniciar el análisis y consultar los resultados mediante las pestañas, visualizaciones y descargas disponibles. Pausa y repetición de la sesión quedan fuera del flujo actual. | Demo del botón de análisis, navegación de resultados y descargas; pausa y repetición pendientes. | IMPRESCINDIBLE | IMPLEMENTADO | 🔵 Implementado |
| 8-Elementos gráficos | Estados de proceso |  | Indicadores visuales para mostrar la carga de archivos, el análisis en curso y la disponibilidad de resultados. | Capturas o demo de los estados del proceso. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| 8-Elementos gráficos | Estados de error |  | Manejo visual de video inválido, landmarks insuficientes o ausencia de API key. El estado de cámara no disponible queda reservado para la función ideal de cámara. | Capturas o pruebas de los estados de error implementados y sus mensajes; estado de cámara pendiente. | IMPRESCINDIBLE | EN_DESARROLLO | 🟡 En desarrollo |

## Diagrama Pipeline

```mermaid
flowchart TD
    A[Cargar video de referencia] --> B[Validar referencia]
    B --> C[Preparar referencia y extraer pose]

    D[Cargar video de ejecución] --> E[Validar ejecución]
    E --> F[Extraer pose y variables]

    G[Cámara: grabar sesión<br/>IDEAL] -.-> E

    C --> H[Sincronizar y segmentar]
    F --> H
    H --> I[Comparar postura y movimiento]
    I --> J[Calcular score]
    J --> K[Identificar segmentos débiles]
    K --> L[Visualizar resultados]
    L --> M[Generar retroalimentación]

    G -.-> P[Feedback perfectamente en tiempo real<br/>IDEAL]
    M --> N[Agente básico<br/>IMPRESCINDIBLE]
    N --> O[Responder preguntas y explicar recomendaciones]
    M -.-> Q[Agente avanzado<br/>IDEAL]
    Q -.-> R[Clips, coaching, progreso y planes de práctica]

    classDef ideal stroke:#d97706,stroke-width:2px,stroke-dasharray:5 5;
    class G,P,Q,R ideal;
```






# Stack Tecnológico

| Tecnología | Uso | Nivel de Prioridad | Estado de avance | Estado de implementación |
| --- | --- | --- | --- | --- |
| Python | Lenguaje principal para el procesamiento de videos, extracción de variables, modelación y lógica de la aplicación. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| UV | Gestión del entorno del proyecto y sus dependencias. | IMPRESCINDIBLE | IMPLEMENTADO | 🔵 Implementado |
| Streamlit | Interfaz inicial de carga, análisis y visualización. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| OpenCV | Lectura, extracción de frames y procesamiento de video. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| MediaPipe | Extracción de landmarks y estimación de pose para el MVP. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| NumPy | Cálculo y transformación de variables numéricas y corporales. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| Pandas | Organización, consulta y análisis tabular de variables y resultados. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| DTW | Alineación temporal de las secuencias de referencia y ejecución. | IMPRESCINDIBLE | VALIDADO | ✅ Validado |
| Streamlit-WebRTC | Captura y procesamiento de video mediante cámara para grabar sesiones del MVP; el feedback perfectamente en tiempo real queda como función ideal. | IDEAL | PENDIENTE | ⚪ No iniciado |
| OpenAI API (Responses API) | Construcción del agente conversacional básico del MVP mediante el cliente oficial y Responses API; las capacidades avanzadas quedan como función ideal. | IMPRESCINDIBLE | IMPLEMENTADO | 🔵 Implementado |
| Angular | Posible evolución futura de la interfaz de la aplicación. | FUTURAS_VERSIONES | PENDIENTE | ⚪ No iniciado |
