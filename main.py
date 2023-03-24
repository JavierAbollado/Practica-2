import time
import random
from multiprocessing import Lock, Condition, Process
from multiprocessing import Value, Array

from hist import History, animate_plot

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


# cronometrar : tiempos totales en cruzar el puente
CRONO_CARS = Value("d", 0.0)
CRONO_PEDS = Value("d", 0.0)

# cronometrar : tiempos totales en ser generados
CRONO_GEN_CARS = Value("d", 0.0)
CRONO_GEN_PEDS = Value("d", 0.0)


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

def ticket_car():
    pass

def ticket_pedestrian():
    pass

def delay_car_north() -> None:
    t = random.normalvariate(TIME_IN_BRIDGE_CARS[0], TIME_IN_BRIDGE_CARS[1])
    time.sleep(max(0,t))

def delay_car_south() -> None:
    t = random.normalvariate(TIME_IN_BRIDGE_CARS[0], TIME_IN_BRIDGE_CARS[1])
    time.sleep(max(0,t))

def delay_pedestrian() -> None:
    t = random.normalvariate(TIME_IN_BRIDGE_PED[0], TIME_IN_BRIDGE_PED[1])
    time.sleep(max(0,t))

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

def main():
    global CRONO_TOTAL, monitor

    # crear el monitor y los procesos de generacion
    monitor = Monitor(n_prints=4*(NCARS+NPEDS))
    gcars = Process(target=gen_cars, args=(monitor,))
    gped = Process(target=gen_pedestrian, args=(monitor,))
    
    # comenzar los procesos
    t = time.time()
    gcars.start()
    gped.start()
    gcars.join()
    gped.join()
    t2 = time.time()
    CRONO_TOTAL = t2 - t
    
    # cambiar "show_image" y "show_gif" para visualizar una imagen o un gif respectivamente
    # save = True -> para guardar los resultados
    animate_plot(monitor.history, show_image=False, show_gif=True, save=False)



if __name__ == "__main__":
    main()
