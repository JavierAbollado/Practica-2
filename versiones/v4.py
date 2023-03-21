import time
import random
from multiprocessing import Lock, Condition, Process, BoundedSemaphore
from multiprocessing import Value, Array

# direcciones
SOUTH = 1
NORTH = 0
index_dir = lambda direction : 0 if direction == NORTH else 1

# para hacer prints
str_dir = lambda direction : "->" if direction == NORTH else "<-" 
str_id  = lambda id : (" "*3 + str(id))[-3:]

# cantidad a producir
NCARS = 20
NPED = 10

# tiempo que pasa entre producciones (distribución exponencial)
TIME_CARS = 0.5
TIME_PED  = 5

# tiempo que tarda en cruzar el puente (distribución normal)
TIME_IN_BRIDGE_CARS = (1, 0.5) 
TIME_IN_BRIDGE_PED  = (10, 5) 

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
        self.nc = Array("i", 2)  # nº de coches en el puente (Norte, Sur)
        self.np = Value("i", 0)  # nº de personas en el puente
        self.cars        = Array("i", 2)  # nº de coches que quieren entrar en el puente : (Norte, Sur)
        self.pedestrians = Value("i", 0)  # nº de personas que quieren entrar en el puente
        
        self.cond_cars = Condition(self.mutex)
        self.cond_peds = Condition(self.mutex)


    def wants_enter_car(self, direction: int) -> None:
        self.mutex.acquire()
        index = index_dir(direction)
        self.cars[index] += 1
        self.mutex.release()

    def enter_car(self, cid : int, direction : int) -> None:
        self.mutex.acquire()
        index = index_dir(direction)
        self.cond_cars.wait_for(
            lambda : 
                (self.nc[index] < N_CARS_IN_BRIDGE and self.nc[1-index] + self.np.value == 0)
        )
        self.nc[index] += 1
        self.cars[index] -= 1
        print(f"[car {str_id(cid)}] enters the bridge.\t{self}")
        if direction == NORTH :
            delay_car_north()
        else:
            delay_car_south()
        print(f"[car {str_id(cid)}] leaving the bridge.\t{self}")
        self.leaves_car(direction)
        self.mutex.release()

    def leaves_car(self, direction: int) -> None:
        self.mutex.acquire() 
        index = index_dir(direction)
        self.nc[index] -= 1
        # 1º avisar a los coches y luego avisar a las personas
        self.cond_cars.notify_all()
        self.cond_peds.notify_all()
        self.mutex.release()

    def wants_enter_pedestrian(self) -> None:
        self.mutex.acquire()
        self.pedestrians.value += 1
        self.mutex.release()

    def enter_pedestrian(self, pid : int) -> None:
        self.mutex.acquire()
        self.cond_peds.wait_for(
            lambda : 
                (self.np.value < N_PED_IN_BRIDGE and self.nc[0] + self.nc[1] == 0)
        )
        print(f"[ped {str_id(pid)}] enters the bridge.\t{self}")
        self.np.value += 1
        print("Value:", self.np.value)
        self.pedestrians.value -= 1
        delay_pedestrian()
        print(f"[ped {str_id(pid)}] leaving the bridge.\t{self}")
        self.leaves_pedestrian()
        self.mutex.release()

    def leaves_pedestrian(self) -> None:
        self.mutex.acquire()
        self.np.value -= 1
        # 1º avisar a las personas y luego avisar a los coches
        self.cond_peds.notify_all()
        self.cond_cars.notify_all()
        self.mutex.release()

    def __repr__(self) -> str:
        return f"Monitor: ({self.pedestrians.value}, {self.cars[0]}, {self.cars[1]})"

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
    print("Crono 1:", CRONO_PEDS.value)
    t = random.normalvariate(TIME_IN_BRIDGE_PED[0], TIME_IN_BRIDGE_PED[1])
    CRONO_PEDS.value += t
    print("Crono 2:", CRONO_PEDS.value)
    print("t :", t)
    time.sleep(max(0,t))

def car(cid: int, direction: int, monitor: Monitor)  -> None:
    print(f"[car {str_id(cid)}] wants to enter ({str_dir(direction)}).\t{monitor}")
    monitor.wants_enter_car(direction)
    monitor.enter_car(cid, direction)
    print(f"[car {str_id(cid)}] out of the bridge.\t{monitor}")

def pedestrian(pid: int, monitor: Monitor) -> None:
    print(f"[ped {str_id(pid)}] wants to enter.\t{monitor}")
    monitor.wants_enter_pedestrian()
    monitor.enter_pedestrian(pid)
    print(f"[ped {str_id(pid)}] out of the bridge.\t{monitor}")

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
    global CRONO_TOTAL
    monitor = Monitor()
    gcars = Process(target=gen_cars, args=(monitor,))
    gped = Process(target=gen_pedestrian, args=(monitor,))
    t = time.time()
    gcars.start()
    gped.start()
    gcars.join()
    gped.join()
    t2 = time.time()
    CRONO_TOTAL = t2 - t



if __name__ == "__main__":
    main()
