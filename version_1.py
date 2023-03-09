"""
Solution to the one-way tunnel
"""

import time
import random
from multiprocessing import Lock, Condition, Process, Semaphore, BoundedSemaphore
from multiprocessing import Value, Array

# direcciones
SOUTH = 1
NORTH = 0

# cantidad a producir
NCARS = 100
NPED = 10

# tiempo que pasa entre producciones (distribución exponencial)
TIME_CARS = 0.5
TIME_PED  = 5

# tiempo que tarda en cruzar el puente (distribución normal)
TIME_IN_BRIDGE_CARS = (1, 0.5) 
TIME_IN_BRIDGE_PED  = (15, 5) 

# máximo nº que caben a la vez en el puente
N_CARS_IN_BRIDGE = 3
N_PED_IN_BRIDGE  = 20

# cronometrar : tiempos totales en cruzar el puente
CRONO_CARS = Value("d", 0.0)
CRONO_PEDS = Value("d", 0.0)

# cronometrar : tiempos totales en ser generados
CRONO_GEN_CARS = Value("d", 0.0)
CRONO_GEN_PEDS = Value("d", 0.0)


class Monitor():
    def __init__(self):
        self.mutex = Lock()
        self.sem = Lock()  # Semaforo actual : cuando se active, será uno de los dos de abajo
        # self.sem_cars_north = BoundedSemaphore(N_CARS_IN_BRIDGE)
        # self.sem_cars_south  = BoundedSemaphore(N_CARS_IN_BRIDGE)
        # self.sem_pedestrian = BoundedSemaphore(N_PED_IN_BRIDGE)
        self.cars        = Array("i", 2)   # [Norte, Sur]
        self.pedestrians = Value("i", 0)

    def wants_enter_car(self, direction: int) -> None:
        self.mutex.acquire()
        index = 0 if direction == NORTH else 1
        self.cars[index] += 1
        self.mutex.release()

    def enter_car(self, cid : int, direction : int) -> None:
        self.sem.acquire()
        print(f"car {cid} heading {direction} enters the bridge. {self}")
        if direction == NORTH :
            delay_car_north()
        else:
            delay_car_south()
        print(f"car {cid} heading {direction} leaving the bridge. {self}")
        self.sem.release()
        self.leaves_car(direction)

    def leaves_car(self, direction: int) -> None:
        self.mutex.acquire() 
        index = 0 if direction == NORTH else 1
        self.cars[index] -= 1
        self.mutex.release()

    def wants_enter_pedestrian(self) -> None:
        self.mutex.acquire()
        self.pedestrians.value += 1
        self.mutex.release()

    def enter_pedestrian(self, pid : int) -> None:
        self.sem.acquire()
        print(f"pedestrian {pid} enters the bridge. {self}")
        delay_pedestrian()
        print(f"pedestrian {pid} leaving the bridge. {self}")
        self.sem.release()
        self.leaves_pedestrian()

    def leaves_pedestrian(self) -> None:
        self.mutex.acquire()
        self.pedestrians.value -= 1
        self.mutex.release()

    def __repr__(self) -> str:
        return f"Monitor: (p,c1,c2) = ({self.pedestrians.value}, {self.cars[0]}, {self.cars[1]})"

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
    time.sleep(max(0,t))

def car(cid: int, direction: int, monitor: Monitor)  -> None:
    print(f"car {cid} heading {direction} wants to enter. {monitor}")
    monitor.wants_enter_car(direction)
    monitor.enter_car(cid, direction)
    print(f"car {cid} heading {direction} out of the bridge. {monitor}")

def pedestrian(pid: int, monitor: Monitor) -> None:
    print(f"pedestrian {pid} wants to enter. {monitor}")
    monitor.wants_enter_pedestrian()
    monitor.enter_pedestrian(pid)
    print(f"pedestrian {pid} out of the bridge. {monitor}")

def gen_pedestrian(monitor: Monitor) -> None:
    pid = 0
    plst = []
    for _ in range(NPED):
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
    monitor = Monitor()
    gcars = Process(target=gen_cars, args=(monitor,))
    gped = Process(target=gen_pedestrian, args=(monitor,))
    gcars.start()
    gped.start()
    gcars.join()
    gped.join()


if __name__ == "__main__":
    main()
