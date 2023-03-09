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
TIME_IN_BRIDGE_PED  = (30, 10) 

# máximo nº que caben a la vez en el puente
N_CARS_IN_BRIDGE = 3
N_PED_IN_BRIDGE  = 20

class Monitor():
    def __init__(self):
        self.mutex = Lock()
        self.sem_cars = BoundedSemaphore(N_CARS_IN_BRIDGE)
        self.sem_pedestrian = BoundedSemaphore(N_PED_IN_BRIDGE)
        self.lcoche   = Array("i", 2)
        self.personas = Value("i", 0)

    def wants_enter_car(self, direction: int) -> None:
        self.mutex.acquire()
        self.lcoche[direction] += 1
        #### código
        self.mutex.release()

    def leaves_car(self, direction: int) -> None:
        self.mutex.acquire() 
        self.lcoche[direction] -= 1
        #### código
        self.mutex.release()

    def wants_enter_pedestrian(self) -> None:
        self.mutex.acquire()
        self.personas.value += 1
        #### código
        self.mutex.release()

    def leaves_pedestrian(self) -> None:
        self.mutex.acquire()
        self.personas.value -= 1
        #### código
        self.mutex.release()

    def __repr__(self) -> str:
        return f"Monitor: {self.personas.value}"

def ticket_car():
    pass

def ticket_pedestrian():
    pass

def delay_car_north() -> None:
    time.sleep(random.normalvariate(TIME_IN_BRIDGE_CARS[0], TIME_IN_BRIDGE_CARS[1]))

def delay_car_south() -> None:
    time.sleep(random.normalvariate(TIME_IN_BRIDGE_CARS[0], TIME_IN_BRIDGE_CARS[1]))

def delay_pedestrian() -> None:
    time.sleep(random.normalvariate(TIME_IN_BRIDGE_PED[0], TIME_IN_BRIDGE_PED[1]))

def car(cid: int, direction: int, monitor: Monitor)  -> None:
    print(f"car {cid} heading {direction} wants to enter. {monitor}")
    monitor.wants_enter_car(direction)
    print(f"car {cid} heading {direction} enters the bridge. {monitor}")
    if direction==NORTH :
        delay_car_north()
    else:
        delay_car_south()
    print(f"car {cid} heading {direction} leaving the bridge. {monitor}")
    monitor.leaves_car(direction)
    print(f"car {cid} heading {direction} out of the bridge. {monitor}")

def pedestrian(pid: int, monitor: Monitor) -> None:
    print(f"pedestrian {pid} wants to enter. {monitor}")
    monitor.wants_enter_pedestrian()
    print(f"pedestrian {pid} enters the bridge. {monitor}")
    delay_pedestrian()
    print(f"pedestrian {pid} leaving the bridge. {monitor}")
    monitor.leaves_pedestrian()
    print(f"pedestrian {pid} out of the bridge. {monitor}")



def gen_pedestrian(monitor: Monitor) -> None:
    pid = 0
    plst = []
    for _ in range(NPED):
        pid += 1
        p = Process(target=pedestrian, args=(pid, monitor))
        p.start()
        plst.append(p)
        time.sleep(random.expovariate(1/TIME_PED))

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
        time.sleep(random.expovariate(1/TIME_CARS))

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
