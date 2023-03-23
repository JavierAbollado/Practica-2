# Practica 2

Tendremos diferentes versiones. Cada una tendrá ciertas restricciones, como el número de coches / personas que pueden estar a la vez en el puente o los órdenes de prioridad de las colas, etc. 

```python
# direcciones
SOUTH = 1
NORTH = 0
index_dir  = lambda dir : 0 if dir == NORTH else 1
change_dir = lambda dir : NORTH if dir == SOUTH else SOUTH

# para hacer prints
str_dir = lambda direction : "->" if direction == NORTH else "<-" 
str_id  = lambda id : (" "*3 + str(id))[-3:]

# cantidad a producir
NCARS = 20
NPEDS = 10

# tiempo que pasa entre producciones (distribución exponencial)
TIME_CARS = 0.5
TIME_PED  = 5

# tiempo que tarda en cruzar el puente (distribución normal)
TIME_IN_BRIDGE_CARS = (1, 0.5) 
TIME_IN_BRIDGE_PED  = (10, 5) 

# máximo nº que caben a la vez en el puente
N_CARS_IN_BRIDGE = 3
N_PEDS_IN_BRIDGE = 20
```

Para cada versión, cronometraremos tiempos y al final haremos unos gráficos para ver los resultados.

```python
# cronometrar : tiempos totales en cruzar el puente
CRONO_CARS = Value("d", 0.0)
CRONO_PEDS = Value("d", 0.0)

# cronometrar : tiempos totales en ser generados
CRONO_GEN_CARS = Value("d", 0.0)
CRONO_GEN_PEDS = Value("d", 0.0)
```

## Versión 1

Solo puede pasar por el puente 1 coche o 1 persona a la vez. Para ello necesitamos únicamente 2 locks:

 1) **mutex**: para todas las funciones de añadir y liberar un coche / persona de las colas.
 2) **lock** : para dejar paso por el puente (solo a uno). 


## Añadir imagenes
<img
  src="/images/hist.gif"
  alt="Historial"
  caption="Evolución de la entrada / salida y esperas del puente">
