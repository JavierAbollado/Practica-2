# Índice - Practica 2

 - [Distribución de archivos](#id0)
 - [Explicación](#id1)
    - [Variables globales](#id1.1)
    - [Importar paquetes](#id1.2)
    - [Monitor](#id1.3)
    - [Distintas soluciones por turnos](#id1.3.0)
       - [Prioridad en uno de los grupos](#id1.3.1)
       - [Tiempo limitado de paso](#id1.3.2)
    - [Delays](#id1.4)
    - [Generador](#id1.5)
    - [Main](#id1.6)
  - [Resultados](#id2)
      
# Distribución de archivos <a name=id0></a>

 - *main.py*: archivo principal a ejecutar.
 - *hist.py*: lo importaremos en el *main.py*, es un archivo con el fin de crear la animación final que se encuentra al final del readme, en él tendremos varias funciones para graficar y un objeto principal *History* para guardar todo el historial. No se explicará mucho el código, pues es complementario.
 - *images/*: para guardar la demostración de inanición y los gif.
 - *versiones/*: evolución de versiones antiguas del trabajo (sin comentar detalladamente).
 
# Explicación <a name=id1></a>

Tenemos el siguiente escenario: 

*Un puente compartido por peatones y vehículos. La anchura del
puente no permite el paso de vehículos en ambos sentidos. Por motivos
de seguridad los peatones y los vehículos no pueden compartir el puente. En el caso de los
peatones, sí que que pueden pasar peatones en sentido contrario.*

## Variables globales <a name=id1.1></a>

Para resolver el problema, primero definimos una serie de constantes, como el número de coches / personas que pueden estar a la vez en el puente, el número de coches / personas a generar, los tiempos que tardan en pasar, etc. 

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

## Importar paquetes <a name=id1.2></a>

Importamos los paquetes necesarios para ejecutar el script

```python
import time
import random
from multiprocessing import Lock, Condition, Process
from multiprocessing import Value, Array

from hist import History, plot, animate_plot
```

donde *hist.py* es un script en el que hemos definido un objeto *History* y alguna función para poder graficar y visualizar mejor los resultados del final. Al finalizar el main, crearemos un gif de la evoción del monitor. Este apartado es complementario al trabajo por lo que no está lo detallado. Se trata de un objeto donde guardamos la información (que solemos hacer con los prints por pantalla) para poder tener una mejor visualización del resultado. No obstante, puesto que su información la recibe directamente cuando hacemos los prints desde el monitor (para no complicarnos), 

```python
class Monitor():
    
    ...
    
    def __repr__(self) -> str:
        waiting = (self.cars[0], self.cars[1], self.peds.value)
        inside  = (self.nc[0]  , self.nc[1]  , self.np.value  )
        self.history.insert(waiting, inside)
        return f"Monitor: ({self.peds.value}, {self.cars[0]}, {self.cars[1]})"
```

no hemos asegurado que la información venga en el orden real pues como ya has comentado en clase, al ejecutar los prints desde distintos procesos puede que algunas líneas se escriban antes que otras que se habían ejecutado antes (en un espacio de tiempo muy junto), pero nos da una visualización general del proceso.

## Monitor <a name=id1.3></a>

Para el puente nos creamos un objeto *Monitor*, en él nos aseguramos de que los invariantes y condiciones de inanición se cumplan. En la hoja hemos supuesto que no hay limite de personas y coches dentro del puente, aunque luego en el código hemos añadido esa restricción para ser más realista. El invariante no lo cambia, simplemente afecta a cuando pueden entrar. Si no quisieramos ningún límite (el cual no sería realista), simplemente hay que quitar las variables ```N_CARS_IN_BRIDGE``` y ```N_PEDS_IN_BRIDGE``` y los condicionales ```self.np < N_PEDS_IN_BRIDGE``` y ```self.nc[i] < N_CARS_IN_BRIDGE``` para i = 0,1.

<image src="/images/invariante_prpa_1.jpg" alt="parte teórica en papel 1">
<image src="/images/invariante_prpa_2.jpg" alt="parte teórica en papel 2">

Para ello cubrimos con locks todas las partes críticas, y en el definimos todas las funciones necesarias para introducir coches, personas y asegurar que cumplen los requisitos pedidos.

```python
class Monitor():
```

 - Inicialización del monitor. Definimos variables para:
 
     - El nº de coches / peatones que hay actualmente dentro del puente (deben ser excluyentes, pues solo puede haber un grupo al mismo tiempo)
     
        - *nc*
        - *np*
 
    - El nº de coches / peatones que hay actualmente esperando para entrar al puente
    
        - *cars*
        - *peds*
    
    - Locks y conditions
    
        - *mutex*: para proteger las secciones críticas.
        - *cond_cars_north*: condición para dejar pasar a los coches (por el norte).
        - *cond_cars_sur*: condición para dejar pasar a los coches (por el sur).
        - *cond_peds*: condición para dejar pasar a los peatones.
    
    - Objeto *History* para guardar el historial (ya comentado)
    
         - *history*

```python
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
```

 - Funciones para la interacción de los coches y el puente.
 
    - **get_cond_cars(dir)**: nos devuelve el objeto condición de los coches (por la dirección *dir*) para poder entrar al puente.  
    
    - **wants_enter_car(dir)**: un coche (por la dirección *dir*) quiere entrar en el puente. Por tanto primero le añadimos a la "cola" del puente ```self.cars[index] += 1```, luego esperamos a que se cumpla la condición de que no haya otros grupos en el puente y que además de los suyos no haya más de ```N_CARS_IN_BRIDGE``` para ser más realista (que no quepan por el puente infinitos coches al mismo tiempo), una vez pasada dicha condición, metemos el coche en el puente, para ello
    
        - lo quitamos de la cola ```self.cars[index] -= 1```.
        - lo añadimos al interior del puente ```self.nc[index] += 1```.
        
       Aseguramos la sección completa (crítica) con el *mutex*.
       
    - **enter_car(dir)**: solo se ocupa de pasar el coche por el puente, es decir, hacer un *delay* del tiempo que tarde en cruzarlo.
    
    - **leaves_car(dir)**: sacamos el coche del puente y hacemos los avisos correspondientes. Para ello primero lo quitamos de la lista de coches dentro del puente ```self.nc[index] -= 1``` y luego avisamos a los demás de que hemos salido.
    
        - Primero avisamos a **un** coche de nuestra dirección para que ocupe nuestro espacio que hemos dejado libre y se mantenga una fluidez en el paso, ```self.get_cond_cars(direction).notify(1)```.
        - En el caso de no haber coches de nuestra dirección a la espera, avismos a los **todos** los coches de la otra dirección y luego **todos** los peatones, con el fin de que algún grupo entre primero, ```self.get_cond_cars(change_dir(direction)).notify_all()```, ```self.cond_peds.notify_all()```. Avisamos a todos para aprovechar el hecho de que caben ```N_CARS_IN_BRIDGE``` coches / ```N_PEDS_IN_BRIDGE``` peatones (respectivamente) a la vez en el puente. 
        
        Aseguramos la sección completa (crítica) con el *mutex*. 

```python
    def get_cond_cars(self, direction):
        return self.cond_cars_north if direction == NORTH else self.cond_cars_south

    def wants_enter_car(self, direction: int) -> None:
        self.mutex.acquire()
        index = index_dir(direction)
        self.cars[index] += 1
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
```

 - Funciones para la interacción de los peatones y el puente (idea análoga a la anterior de los coches).
     
    - **wants_enter_pedestrian()**: un peatón quiere entrar en el puente. Por tanto primero le añadimos a la "cola" del puente ```self.peds.value += 1```, luego esperamos a que se cumpla la condición de que no haya otros grupos en el puente y que además de los suyos no haya más de ```N_PEDS_IN_BRIDGE``` para ser más realista (que no quepan por el puente infinitos peatones al mismo tiempo), una vez pasada dicha condición, metemos el coche en el puente, para ello
    
        - lo quitamos de la cola ```self.peds.value -= 1```.
        - lo añadimos al interior del puente ```self.np.value += 1```.
        
       Aseguramos la sección completa (crítica) con el *mutex*.
       
    - **enter_pedestrian()**: solo se ocupa de pasar el peatón por el puente, es decir, hacer un *delay* del tiempo que tarde en cruzarlo.
    
    - **leaves_pedestrian()**: sacamos el peatón del puente y hacemos los avisos correspondientes. Para ello primero lo quitamos de la lista de peatones dentro del puente ```self.np.value -= 1``` y luego avisamos a los demás de que hemos salido.
    
        - Primero avisamos a **un** peatón para que ocupe nuestro espacio que hemos dejado libre y se mantenga una fluidez en el paso, ```self.cond_peds.notify(1)```.
        - En el caso de no haber peatones a la espera, avismos a los **todos** los coches (de las dos direcciones), con el fin de que algún grupo entre primero, ```self.cond_cars_north.notify_all()```, ```self.cond_cars_south.notify_all()```. Avisamos a todos para aprovechar el hecho de que caben ```N_CARS_IN_BRIDGE``` coches a la vez en el puente. 
        
        Aseguramos la sección completa (crítica) con el *mutex*. 

```python
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
```

 - Por último como ya comentamos, en la representación del puente añadimos un paso auxiliar para que cada vez que printeemos por pantalla información, la vayamos guardando en nuestro historial.

```python
    def __repr__(self) -> str:
        waiting = (self.cars[0], self.cars[1], self.peds.value)
        inside  = (self.nc[0]  , self.nc[1]  , self.np.value  )
        self.history.insert(waiting, inside)
        return f"Monitor: ({self.peds.value}, {self.cars[0]}, {self.cars[1]})"
```

## Distintas soluciones por turnos <a name=id1.3.0></a>

En mi caso he optado por seguir introduciendo en el puente el grupo actualmente dentro para mantener la fluidez, teniendo en cuenta que en la realidad estar todo el rato cambiando de grupos tarda tiempo (coches que estaban pasando frenan y dejan de pasar, se apartan y comienzan a arrancar los demás, en el caso de los peatones es instantáneo). Sin embargo también podemos hacer distintas versiones (a gusto del diseñador, cada uno con sus ventajas y desventajas)

### Prioridad en uno de los grupos <a name=id1.3.1></a>
 
 Idea: Por ejemplo supongamos que queremos que los peatones tengan prioridad de paso ante todos, entonces si están pasando los coches (da igual la dirección) y quiere entrar un peaton, dejamos de pasar los coches (esperamos a que terminen de pasar los que están dentro) y comenzamos a pasar a los peatones, para ello 
 
   - Añadimos a la condición de entrada de los coches ```(self.nc[index] < N_CARS_IN_BRIDGE and self.nc[1-index] + self.np.value == 0)```, la condición ```self.peds.value == 0``` (con un *and*). Para checkear que no hay peatones esperando.
   
   - Cambiamos los avisos de salida del puente de 
   
```python
   index = index_dir(direction)
   (...)
   self.get_cond_cars(direction).notify(1)
   self.get_cond_cars(change_dir(direction)).notify_all()
   self.cond_peds.notify_all()
```

  a 
   
```python
  index = index_dir(direction)
  (...)
  # si hay peatones esperando, les avisamos
  if self.peds.value > 0:
      self.cond_peds.notify_all()
  # si no, si hay coches de nuestra dirección esperando, avisamos a uno
  elif self.cars[index] > 0:
      self.get_cond_cars(direction).notify(1)
  # si no, avismos a los demás coches
  else:
      self.get_cond_cars(change_dir(direction)).notify_all()
```

### Tiempo limitado de paso <a name=id1.3.2></a>
 
 Idea: que no puedan estar X (variable global) tiempo seguido pasando el mismo grupo y deje a todos los demas bloqueados. 
 
 Para ello añadimos una variable en el init que guarde en que momento a comenzado a entrar un grupo, ```self.t = Value("f", time.time())```. Y cada vez que un nuevo grupo entra en el puente (es decir su número actual dentro del puente es 0) la actualiza, es decir en las funciones *wants_enter_car* y *wants_enter_pedestrian*, justo después de pasar la condición hacemos un 
 
```python
    if NUM == 0:
        self.t.value = time.time()
```

  donde *NUM* es *self.np* en *wants_enter_pedestrian* y *self.nc[index]* en *wants_enter_car* (con su respectivo index). Una vez tenemos disponible dicha información actualmos al similar al caso anterior. Para ello, veamos como cambiaría en la sección de los coches (de personas sería análogo), 
 
   - Añadimos a las condiciones de entrada ```(self.nc[index] < N_CARS_IN_BRIDGE and self.nc[1-index] + self.np.value == 0)``` la condición ```(time.time() - self.t.value < X or self.peds.value + self.cars[1-index] == 0)```, para que entremos solo si llevamos menos tiempo entrando del propuesto como límite, X, o no hay más grupos que quieran entrar.
  
   - Cambiamos los avisos de salida del puente de 
   
```python
   index = index_dir(direction)
   (...)
   self.get_cond_cars(direction).notify(1)
   self.get_cond_cars(change_dir(direction)).notify_all()
   self.cond_peds.notify_all()
```

  a 
   
```python
  index = index_dir(direction)
  (...)
  # si cumplimos las condiciones seguimos llamando a los de nuestro grupo
  if time.time() - self.t.value < X or self.peds.value + self.cars[1-index] == 0:
      self.get_cond_cars(direction).notify(1)
  # si no, si los otros coches están esperando, les avisamos
  elif self.cars[1-index] > 0:
      self.get_cond_cars(change_dir(direction)).notify_all()
  # si no, avisamos a los peatones
  else:
      self.cond_peds.notify_all()
```

## Delays <a name=id1.4></a>

Definimos funciones para los tiempos que tardan en pasar cada uno por el puente. Las funciones *ticket* habían sido creadas con el fin de también introducir un tiempo que se tarda en coger un ticket para poder entrar al puente, pero al final solo era esperar más por lo que lo he obviado.   

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

## Generador <a name=id1.5></a>

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
        time.sleep(t)

    for p in plst:
        p.join()
```

## Main <a name=id1.6></a>

Por último para ejecutar todo el proceso ejecutamos el *main* que comienza los procesos de generación de coches y personas. La variable *CRONO_TOTAL* nos dice el tiempo que ha tardado en ejecutar todo el proceso.

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

# Resultados <a name=id2></a>

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
