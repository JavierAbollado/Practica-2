from multiprocessing import Array
import matplotlib.pyplot as plt


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
      

def plot(history : History) -> None:
    size = history.size()
    
    # get data
    x = range(size)
    y0_cars_north = [history.history[0][0][i] for i in range(size)]
    y0_cars_south = [history.history[0][1][i] for i in range(size)]
    y0_peds       = [history.history[0][2][i] for i in range(size)]
    y1_cars_north = [history.history[1][0][i] for i in range(size)]
    y1_cars_south = [history.history[1][1][i] for i in range(size)]
    y1_peds       = [history.history[1][2][i] for i in range(size)]
    
    # plot waiting & inside
    fig, (ax1,ax2) = plt.subplots(2,1, figsize=(12,7))
    ax1.set_title("Waiting History")
    ax1.plot(x, y0_cars_north, "r-", label="cars north")
    ax1.plot(x, y0_cars_south, "g-", label="cars south")
    ax1.plot(x, y0_peds, "b-", label="pedestrians")
    ax1.legend()
    ax2.set_title("Inside Bridge History")
    ax2.plot(x, y1_cars_north, "r-", label="cars north")
    ax2.plot(x, y1_cars_south, "g-", label="cars south")
    ax2.plot(x, y1_peds, "b-", label="pedestrians")
    ax2.legend()
    fig.show()
