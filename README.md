# Practica-2

Tendremos diferentes versiones. Cada una tendrá ciertas restricciones, como el número de coches / personas que pueden estar a la vez en el puente o los órdenes de prioridad de las colas, etc. 

## Versión 1

Solo puede pasar por el puente 1 coche o una persona a la vez. Hay 2 locks:

 - mutex: para todas las funciones de añadir y liberar un coche / persona de las colas.
 - lock : para dejar paso por el puente (solo a uno). 
