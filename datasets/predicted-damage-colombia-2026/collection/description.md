Creamos evaluaciones de daños a nivel de edificio tras el terremoto en Colombia
mediante el entrenamiento y la posterior ejecución de un modelo de inteligencia
artificial sobre imágenes satelitales adquiridas después del desastre. El modelo
de IA clasifica cada edificio identificado en las imágenes como "sin daños",
"afectado" o "desconocido". La categoría "desconocido" se utiliza cuando el
edificio no puede ser evaluado adecuadamente, por ejemplo, debido a la presencia
de nubes. Utilizamos los polígonos de edificios de Overture Maps, que representan
el estado de las edificaciones sobre el terreno antes del evento. Los resultados
se distribuyen como un archivo vectorial en formato GeoPackage, con los
siguientes atributos para cada edificio:

- `id` – identificador único de Overture Maps y Google para cada edificio.
- `damaged` – valor 1 si el edificio está dañado; de lo contrario, 0.
- `unknown` – valor 1 si el edificio está cubierto por nubes, neblina, humo o
  si, por alguna otra razón, no fue posible clasificarlo; de lo contrario, 0.
- `area` – área del edificio en metros cuadrados.

We create building level damage assessments by training and then running an AI
model on the post-disaster imagery. The AI model predicts whether each footprint
in the imagery is "building", "damaged", or "unknown" (i.e. cloudy). We use
Overture Maps and Google building footprints which represent the state on the
ground pre-event and distribute the resulting data as a vector file GeoPackage
with the following per-footprint attributes:

- `id` – the Overture Maps unique ID for each footprint.
- `damaged` – 1 if the building is damaged, else 0.
- `unknown` – 1 if the building was covered by clouds/haze/smoke or otherwise
  unable to be classified, else 0.
- `area` – area of the building in sq meters.
