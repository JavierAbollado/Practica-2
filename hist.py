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
    
    # plot waiting outside the bridge
    ax1.set_title("Evolucion de la lista de espera del puente")
    ax1.plot(x[:t], y[0,0,:t], "r-", label="coches - norte")
    ax1.plot(x[:t], y[0,1,:t], "g-", label="coches - sur")
    ax1.plot(x[:t], y[0,2,:t], "b-", label="personas")
    ax1.set_xlim(0,len(x)+1)
    ax1.set_ylim(0,y[0].max()+1)
    ax1.legend()
    
    # plot inside bridge
    ax2.set_title("Evolucion del nº de individuos dentro del puente")
    ax2.plot(x[:t], y[1,0,:t], "r-", label="coches - norte")
    ax2.plot(x[:t], y[1,1,:t], "g-", label="coches - sur")
    ax2.plot(x[:t], y[1,2,:t], "b-", label="personas")
    ax2.set_xlim(0,len(x)+1)
    ax2.set_ylim(0,y[1].max()+1)
    ax2.legend()


def animate_plot(history : History, save=False, show_image=True, show_gif=False) -> None:
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
    if show_gif:
        fig, (ax1,ax2) = plt.subplots(2,1, figsize=(12,7))
        ts = range(1, size+1)
        ani = animation.FuncAnimation(fig, plot, ts, fargs=[ax1, ax2, x, y], interval=25)
        if save:
            ani.save("images/prueba.gif")
    
    # create image
    if show_image:
        _fig, (_ax1,_ax2) = plt.subplots(2,1, figsize=(12,7))
        plot(size+1, _ax1, _ax2, x, y)
        if save:
            _fig.savefig("images/prueba.png")
            
    plt.show()
