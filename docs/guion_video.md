# Alento: guion del video (6 minutos)

**Proyecto:** Alento, plataforma de inteligencia de negocios para la admisión, depuración y verificación del aire
**Asignatura:** Inteligencia de Negocios, Universidad Manuela Beltrán, 2026
**Presentan:** Sergio Martínez Castañeda (S), Diego Rojas Martínez (D) y Joel Lancheros (J)
**Duración objetivo:** 5:45 a 6:00 minutos, a ritmo de lectura natural (unas 620 palabras habladas, más las pausas de la demostración).

> Antes de grabar: abra el tablero con los datos cargados, tenga a mano el informe en la Figura 1 y deje el panel «Nuevo tratamiento» listo. Grabe en 1080p y suba el video a YouTube como «No listado».

---

## 0:00 a 0:40. Presentación y problema (S)
**En pantalla:** portada del informe con el logo de la UMB y luego el tablero.

**S:** Hola, somos Sergio Martínez, Diego Rojas y Joel Lancheros, de Inteligencia de Negocios de la Universidad Manuela Beltrán, con el profesor Juan José Osorio. La actividad pide una aplicación que mida el aire contaminado, lo depure, verifique el resultado y lo convierta en información para decidir. Nuestra respuesta se llama Alento. Como no teníamos sensores reales, simulamos la cámara con un modelo físico, pero dejamos la entrada de datos lista para cambiarla por hardware.

## 0:40 a 1:30. Arquitectura (D)
**En pantalla:** Figura 1, arquitectura de dos ductos.

**D:** Pensamos el sistema como dos ductos. Arriba va el camino del aire: admisión, cámara de mezcla de 12 metros cúbicos, tren de filtros y verificación. Abajo va el camino del dato: un puerto de sensores, una API en FastAPI, una base de datos PostgreSQL, una capa analítica en pandas y un tablero en React. La API recibe lecturas por tres rutas, abrir lote, registrar lecturas y cerrar lote. Por eso cambiar el simulador por una placa con sensores no obliga a tocar la lógica de negocio.

## 1:30 a 2:20. Datos y módulos 1 a 3 (J)
**En pantalla:** Figura 3, modelo de datos, y luego el ciclo del lote.

**J:** La unidad de trabajo es el lote, un tratamiento completo. Cada lote tiene tres etapas: entrada, con tres lecturas; proceso, con una lectura cada 30 segundos; y salida, con tres lecturas. Cada lectura guarda PM2.5, PM10, CO2 y CO. El módulo 1 monitorea y calcula un nivel de severidad. El módulo 2 aplica un tren de hasta cinco filtros: prefiltro, HEPA, carbón activado, catalizador y absorbente de CO2. El módulo 3 vuelve a medir, compara con la norma colombiana, la Resolución 2254 de 2017, y con la guía de la OMS 2021, y clasifica el resultado.

## 2:20 a 3:20. Demostración en vivo (S)
**En pantalla:** panel «Nuevo tratamiento».

**S:** Veamos un tratamiento. Elijo aire de vía urbana y pido la sugerencia. El sistema recomienda HEPA con prefiltro, porque el problema principal son las partículas, y estima cuántos minutos tardará. Lo ejecuto. Aquí aparece la curva de depuración: los puntos son las lecturas, la línea es el ajuste y la discontinua es lo que predecía el catálogo. Al cerrar el lote, el PM2.5 baja de más de 80 a menos de 10 microgramos por metro cúbico y el lote queda clasificado como «cumple guías OMS».

## 3:20 a 4:30. Módulo 4: dashboard (D)
**En pantalla:** indicadores y visualizaciones del tablero.

**D:** El tablero tiene los cuatro indicadores pedidos: PM2.5 antes y después, CO2 en ppm, porcentaje de reducción y minutos de purificación. Sobre 320 tratamientos simulados, el PM2.5 baja en promedio de 83,4 a 7,8, una reducción de 90,6 %. El CO2 solo baja 23,4 %, y es el hallazgo más útil: sin el absorbente casi no se mueve. Con HEPA el PM2.5 baja 95,3 % frente a 21,6 % sin ella, y con catalizador el CO cae 77,7 % frente a 5,1 %. Además hay un reloj del aire con las horas pico, que coinciden con el tráfico de las 18:00, una comparación de trenes de filtros y un panel de alertas ordenadas por severidad.

## 4:30 a 5:30. Componente de inteligencia (J)
**En pantalla:** Figura 10, validación del modelo, y panel de alertas.

**J:** El componente de inteligencia tiene tres partes. Primero, un recomendador que escoge los filtros según el contaminante dominante. Segundo, reglas de alerta, por ejemplo ingreso sobre la norma, baja eficiencia o filtro que no aplica, y un control EWMA que detecta lecturas de ingreso anómalas. Tercero, un modelo de regresión log-lineal que predice cuántos minutos tarda un lote en llegar a la meta. Lo validamos en el tiempo: se entrena con los primeros lotes y predice los últimos. El error medio fue de 0,97 minutos, frente a 7,17 de una referencia ingenua, con R cuadrado de 0,97.

## 5:30 a 6:00. Limitaciones y cierre (S)
**En pantalla:** repositorio en GitHub.

**S:** Para ser honestos: los datos son simulados, el modelo físico supone mezcla perfecta y las eficiencias de los filtros son estimaciones de ingeniería. Los resultados muestran cómo se comporta el sistema, no un ensayo de laboratorio. El siguiente paso es conectar sensores reales y recalibrar. El código, la base de datos, las pruebas y el informe están en nuestro repositorio de GitHub. Gracias por su atención.

---

## Lista de verificación antes de subir
- El video dura 6:00 o menos.
- Se ven el tablero, la demostración y el repositorio.
- Se menciona que los datos son simulados.
- El enlace de YouTube se pega en el informe y en el README.
