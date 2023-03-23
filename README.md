# Practica 2

Primero definimos una serie de constantes, como el número de coches / personas que pueden estar a la vez en el puente, el número de coches / personas a generar, los tiempos que tardan en pasar, etc. 

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

## Import

Importamos los paquetes necesarios para ejecutar el script

```python
import time
import random
from multiprocessing import Lock, Condition, Process
from multiprocessing import Value, Array

from hist import History, plot, animate_plot
```

donde hist.py es un script en el que hemos definido un objeto *History* y alguna función para poder graficar y visualizar mejor los resultados del final. Al finalizar el main, crearemos un gif de la evoción del monitor.

```python
from multiprocessing import Array, Value
import matplotlib.pyplot as plt
from matplotlib import animation
import numpy as np


class History:

    def __init__(self, N=100):

        self.N = N
        self.n = Value("i", 0)

        self.history = self.create_new_block()

    def create_new_block(self):

        waiting_cars_north = Array("i", self.N) 
        waiting_cars_south = Array("i", self.N) 
        waiting_peds       = Array("i", self.N) 
        
        inside_cars_north  = Array("i", self.N) 
        inside_cars_south  = Array("i", self.N) 
        inside_peds        = Array("i", self.N) 
        
        block = [
            (waiting_cars_north, waiting_cars_south, waiting_peds), 
            (inside_cars_north, inside_cars_south, inside_peds)
        ]

        return block

    def insert(self, waiting, inside):

        self.history[0][1][self.n.value] = waiting[1]
        self.history[0][2][self.n.value] = waiting[2]
        self.history[0][0][self.n.value] = waiting[0]

        self.history[1][0][self.n.value] = inside[0]
        self.history[1][1][self.n.value] = inside[1]
        self.history[1][2][self.n.value] = inside[2]
        
        self.n.value = self.n.value + 1

    def size(self):
        return self.n.value
      

def plot(t, ax1, ax2, x, y):
    # clear plot
    ax1.clear()
    ax2.clear()
    # plot waiting & inside
    ax1.set_title("Evolucion de la lista de espera del puente")
    ax1.plot(x[:t], y[0,0,:t], "r-", label="coches - norte")
    ax1.plot(x[:t], y[0,1,:t], "g-", label="coches - sur")
    ax1.plot(x[:t], y[0,2,:t], "b-", label="personas")
    ax1.set_xlim(0,len(x)+1)
    ax1.set_ylim(0,y[0].max()+1)
    ax1.legend()
    ax2.set_title("Evolucion del nº de individuos dentro del puente")
    ax2.plot(x[:t], y[1,0,:t], "r-", label="coches - norte")
    ax2.plot(x[:t], y[1,1,:t], "g-", label="coches - sur")
    ax2.plot(x[:t], y[1,2,:t], "b-", label="personas")
    ax2.set_xlim(0,len(x)+1)
    ax2.set_ylim(0,y[1].max()+1)
    ax2.legend()


def animate_plot(history : History, save=False) -> None:
    size = history.size()
    # get data
    x = range(size)
    y0_cars_north = [history.history[0][0][i] for i in x]
    y0_cars_south = [history.history[0][1][i] for i in x]
    y0_peds       = [history.history[0][2][i] for i in x]
    y1_cars_north = [history.history[1][0][i] for i in x]
    y1_cars_south = [history.history[1][1][i] for i in x]
    y1_peds       = [history.history[1][2][i] for i in x]
    y = np.array([[y0_cars_north, y0_cars_south, y0_peds], [y1_cars_north, y1_cars_south, y1_peds]])
    # create gif
    fig, (ax1,ax2) = plt.subplots(2,1, figsize=(12,7))
    ts = range(1, size+1)
    ani = animation.FuncAnimation(fig, plot, ts, fargs=[ax1, ax2, x, y], interval=25)
    if save:
        ani.save("images/hist.gif")
    plt.show()
```

## Monitor

Para el puente nos creamos un objeto *Monitor*, en él nos aseguramos de que los invariantes y condiciones de inanición se cumplan. En la hoja hemos supuesto que no hay limite de personas y coches dentro del puente, aunque luego en el código hemos añadido esa restricción para ser más realista. El invariante no lo cambia, simplemente afecta a cuando pueden entrar. Si no quisieramos ningún límite (el cual no sería realista), simplemente hay que quitar las variables ```N_CARS_IN_BRIDGE``` y ```N_PEDS_IN_BRIDGE``` y los condicionales ```self.np < N_PEDS_IN_BRIDGE``` y ```self.nc[i] < N_CARS_IN_BRIDGE``` para i = 0,1.

<image src="/images/invariante_prpa_1.jpg" alt="parte teórica en papel 1">
<image src="/images/invariante_prpa_2.jpg" alt="parte teórica en papel 2">

Para ello cubrimos con locks todas las partes críticas, y en el definimos todas las funciones necesarias para introducir coches, personas y asegurar que cumplen los requisitos pedidos.

```python
class Monitor():

    def __init__(self, n_prints):

        # nº dentro del puente
        self.nc = Array("i", 2)  # coches (Norte, Sur)
        self.np = Value("i", 0)  # personas

        # nº esperando a la cola
        self.cars = Array("i", 2)  # coches (Norte, Sur)
        self.peds = Value("i", 0)  # personas
        
        # locks & conditions
        self.mutex = Lock()
        self.cond_cars_north = Condition(self.mutex)
        self.cond_cars_south = Condition(self.mutex)
        self.cond_peds       = Condition(self.mutex)

        # historial de la entrada / salida y esperas del puente 
        self.history = History(n_prints)

    def get_cond_cars(self, direction):
        return self.cond_cars_north if direction == NORTH else self.cond_cars_south

    def wants_enter_car(self, direction: int) -> None:
        self.mutex.acquire()
        index = index_dir(direction)
        self.cars[index] += 1
        index = index_dir(direction)
        self.get_cond_cars(direction).wait_for(
            lambda : 
                (self.nc[index] < N_CARS_IN_BRIDGE and self.nc[1-index] + self.np.value == 0)
        )
        self.nc[index] += 1
        self.cars[index] -= 1
        self.mutex.release()

    def enter_car(self, direction : int) -> None:
        if direction == NORTH :
            delay_car_north()
        else:
            delay_car_south()

    def leaves_car(self, direction: int) -> None:
        self.mutex.acquire() 
        index = index_dir(direction)
        self.nc[index] -= 1
        # 1º avisar a un coche (ocupando el espacio del que acaba de salir) 
        # y luego avisar a los otros coches y las personas (en caso de que hayan terminado de pasar estos coches)
        self.get_cond_cars(direction).notify(1)
        self.get_cond_cars(change_dir(direction)).notify_all()
        self.cond_peds.notify_all()
        self.mutex.release()
    
    def wants_enter_pedestrian(self) -> None:
        self.mutex.acquire()
        self.peds.value += 1
        self.cond_peds.wait_for(
            lambda : 
                (self.np.value < N_PEDS_IN_BRIDGE and self.nc[0] + self.nc[1] == 0)
        )
        self.np.value += 1
        self.peds.value -= 1
        self.mutex.release()

    def enter_pedestrian(self) -> None:
        delay_pedestrian()

    def leaves_pedestrian(self) -> None:
        self.mutex.acquire()
        self.np.value -= 1
        # 1º avisar a una persona (ocupando el espacio del que se acaba de ir) 
        # y luego avisar a los coches (por si ya han terminado de pasar las personas)
        self.cond_peds.notify(1)
        self.cond_cars_north.notify_all()
        self.cond_cars_south.notify_all()
        self.mutex.release()

    def __repr__(self) -> str:
        waiting = (self.cars[0], self.cars[1], self.peds.value)
        inside  = (self.nc[0]  , self.nc[1]  , self.np.value  )
        self.history.insert(waiting, inside)
        return f"Monitor: ({self.peds.value}, {self.cars[0]}, {self.cars[1]})"
```

por último definimos funciones para los tiempos que tardan en pasar cada uno por el puente

```python
def ticket_car():
    pass

def ticket_pedestrian():
    pass

def delay_car_north() -> None:
    t = random.normalvariate(TIME_IN_BRIDGE_CARS[0], TIME_IN_BRIDGE_CARS[1])
    CRONO_CARS.value += t
    time.sleep(max(0,t))

def delay_car_south() -> None:
    t = random.normalvariate(TIME_IN_BRIDGE_CARS[0], TIME_IN_BRIDGE_CARS[1])
    CRONO_CARS.value += t
    time.sleep(max(0,t))

def delay_pedestrian() -> None:
    t = random.normalvariate(TIME_IN_BRIDGE_PED[0], TIME_IN_BRIDGE_PED[1])
    CRONO_PEDS.value += t
    print("t :", t)
    time.sleep(max(0,t))
```

## Generador 

Este apartado permitirá generar distintos coches (aleatoriamente por el norte o por el sur) y distintas personas. Según se vayan creando las irá introduciendo por el puente. Las funciones de generar son *gen_cars* y *gen_pedestrians*, mientras que las funciones *car* y *pedestrian* se encargan individualmente de que cada coche y persona respectivamente, entre y salga del puente cuando llegue su turno.

```python 
def car(cid: int, direction: int, monitor: Monitor)  -> None:
    print(f"[car {str_id(cid)}] wants to enter ({str_dir(direction)}).\t{monitor}")
    monitor.wants_enter_car(direction)
    print(f"[car {str_id(cid)}] enters the bridge.\t{monitor}")
    monitor.enter_car(direction)
    print(f"[car {str_id(cid)}] leaving the bridge.\t{monitor}")
    monitor.leaves_car(direction)
    print(f"[car {str_id(cid)}] out of the bridge.\t{monitor}")

def pedestrian(pid: int, monitor: Monitor) -> None:
    print(f"[ped {str_id(pid)}] wants to enter.\t{monitor}")
    monitor.wants_enter_pedestrian()
    print(f"[ped {str_id(pid)}] enters the bridge.\t{monitor}")
    monitor.enter_pedestrian()
    print(f"[ped {str_id(pid)}] leaving the bridge.\t{monitor}")
    monitor.leaves_pedestrian()
    print(f"[ped {str_id(pid)}] out of the bridge.\t{monitor}")

def gen_pedestrian(monitor: Monitor) -> None:
    pid = 0
    plst = []
    for _ in range(NPEDS):
        pid += 1
        p = Process(target=pedestrian, args=(pid, monitor))
        p.start()
        plst.append(p)
        t = random.expovariate(1/TIME_PED)
        CRONO_GEN_PEDS.value += t
        time.sleep(t)

    for p in plst:
        p.join()

def gen_cars(monitor: Monitor) -> None:
    cid = 0
    plst = []
    for _ in range(NCARS):
        direction = NORTH if random.randint(0,1)==1  else SOUTH
        cid += 1
        p = Process(target=car, args=(cid, direction, monitor))
        p.start()
        plst.append(p)
        t = random.expovariate(1/TIME_CARS)
        CRONO_GEN_CARS.value += t
        time.sleep(t)

    for p in plst:
        p.join()
```

## Main

Por último para ejecutar todo el proceso ejecutamos el *main* que comienza los procesos de generación de coches y personas.

```python
if __name__ == "__main__":
    global CRONO_TOTAL, monitor
    monitor = Monitor(n_prints=4*(NCARS+NPEDS))
    gcars = Process(target=gen_cars, args=(monitor,))
    gped = Process(target=gen_pedestrian, args=(monitor,))
    t = time.time()
    gcars.start()
    gped.start()
    gcars.join()
    gped.join()
    t2 = time.time()
    CRONO_TOTAL = t2 - t
    animate_plot(monitor.history)
```

## Resultados

Podemos observar como efectivamente únicamente uno de los tres grupos se encuentra dentro del puente al mismo tiempo. Además se puede comprobar también que el número máximo de personas y coches dentro del puente es ```N_CARS_IN_BRIDGE = 3``` y ```N_PEDS_IN_BRIDGE = 20``` respectivamente, como era de esperar.   

<img
  src="/images/hist.gif"
  alt="Historial"
  caption="Evolución de la entrada / salida y esperas del puente">

Siendo así el resultado final:

<img
  src="/images/hist.png"
  alt="Historial_imagen"
  caption="Evolución de la entrada / salida y esperas del puente_imagen">
