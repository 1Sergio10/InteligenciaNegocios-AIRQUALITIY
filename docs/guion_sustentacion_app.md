# Alento: guion de sustentación con la aplicación en vivo (6 minutos)

**Antes de empezar:** tenga abierto `http://localhost:8000` en la parte superior de la página, con el zoom del navegador en 90 %. Tenga el repositorio de GitHub y el informe en otras pestañas. Reparto: Sergio (S), Diego (D) y Joel (J). Unas 800 palabras habladas.

---

## 0:00 a 0:35. Qué es Alento (S)
**Pantalla:** parte superior del tablero.

**S:** Buenos días. Somos Sergio Martínez, Diego Rojas y Joel Lancheros. Presentamos Alento, una plataforma de inteligencia de negocios para tres momentos del aire: cuando entra contaminado, cuando se depura y cuando se verifica. Lo que ven es la aplicación funcionando. Los datos son simulados con un modelo físico de cámara, porque no teníamos sensores, pero la entrada es intercambiable por lecturas reales.

## 0:35 a 1:30. Los cuatro indicadores (D)
**Pantalla:** fila de indicadores. Señale cada uno con el cursor.

**D:** Arriba están los cuatro indicadores que pide la guía. El PM2.5 de ingreso es de 83,4 microgramos por metro cúbico y a la salida baja a 7,8. Eso es una reducción de 90,6 %. El CO2 es el indicador que sorprende: entra en 1.322 ppm y sale en 1.013, solo 23 % menos, porque ningún filtro de partículas lo toca. Y el cuarto indicador es el tiempo de purificación en minutos. Todo se calcula sobre los 320 tratamientos que hay en la base de datos.

## 1:30 a 2:25. Distancia a la norma y reloj del aire (D)
**Pantalla:** gráfico de distancia a la norma y luego el reloj.

**D:** Este gráfico compara cada contaminante con su límite. El punto ocre es el aire que entra y el verde, el que sale, en escala logarítmica. Los límites son los de la Resolución 2254 de 2017 y la guía de la OMS de 2021. Aquí se ve que las partículas quedan por debajo de la guía, mientras que el CO2 sigue lejos de la meta. Más abajo, el reloj del aire muestra el PM2.5 por hora del día: el pico está a las 18:00, con unos 125 microgramos, porque coincide con el tráfico de la tarde.

## 2:25 a 3:40. Demostración: un tratamiento nuevo (S)
**Pantalla:** panel «Nuevo tratamiento».

**S:** Ahora creamos un tratamiento. Elijo aire de vía urbana. Pido la sugerencia, y el sistema recomienda un prefiltro con HEPA, porque en ese aire dominan las partículas, y me dice cuántos minutos estima que tardará. Lo ejecuto. Se registran tres lecturas de entrada, una lectura cada 30 segundos durante el proceso y tres lecturas de salida. Al terminar, el lote queda clasificado, por ejemplo «cumple guías OMS», con su nivel de severidad antes y después.

## 3:40 a 4:20. Curva de depuración (S)
**Pantalla:** curva del lote recién creado.

**S:** Esta es la curva del lote. Los puntos son las lecturas, la línea continua es el ajuste y la discontinua es lo que habría pasado si los filtros funcionaran como dice el catálogo. Cuando las dos curvas se separan, la planta no se comporta como las fichas técnicas. Con el selector arriba puedo cambiar entre PM2.5, PM10, CO2 y CO.

## 4:20 a 5:00. Comparación de trenes y alertas (J)
**Pantalla:** gráfico de trenes de filtros y panel de alertas.

**J:** Aquí se comparan los trenes de filtros. Con HEPA el PM2.5 baja 95 % y sin ella 22 %. Con catalizador el CO cae 78 % frente a 5 %. La conclusión de negocio es que elegir el tren pesa más que la calidad de cada filtro. A la derecha, las alertas ordenadas por severidad: ingreso sobre la norma, salida sobre la norma, baja eficiencia, filtro que no aplica y anomalía en el ingreso.

## 5:00 a 5:40. Inteligencia: el modelo de tiempo (J)
**Pantalla:** gráfico de validación del modelo.

**J:** El componente de inteligencia predice cuántos minutos tarda un lote en cumplir la meta. Es una regresión log-lineal por tren de filtros. La validamos en el tiempo: entrenamos con los primeros lotes y predecimos los últimos. El error medio es de 0,97 minutos, contra 7,17 de una referencia ingenua, con un R cuadrado de 0,97. Además, un control EWMA marca los ingresos anómalos.

## 5:40 a 6:00. Informe y cierre (S)
**Pantalla:** panel del informe y, si hay tiempo, el repositorio.

**S:** Por último, el informe para decidir se redacta a partir de los datos y se puede descargar en CSV. Las limitaciones son claras: los datos son simulados y el modelo supone mezcla perfecta. El siguiente paso es conectar sensores reales. Todo el código, las pruebas y este informe están en GitHub. Gracias.

---

## Si le sobra o le falta tiempo
- **Falta tiempo:** omita el reloj del aire y la curva de depuración y deje un solo ejemplo de comparación de trenes.
- **Sobra tiempo:** ejecute un segundo tratamiento con aire de «quema de biomasa» y compare qué tren recomienda.
- **Si el tratamiento en vivo falla:** use las capturas de `docs/capturas`.
