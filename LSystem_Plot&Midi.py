
# MIDI extension: 
# CTL in  trigger new iteration

from music21 import chord, metadata, stream
import mido
import matplotlib.pyplot as plt
import time

def plot_evolution(evolution):
    plt.figure(figsize=(10, 10))
    plt.imshow(evolution, cmap='binary', interpolation='nearest')
    plt.xticks([])  
    plt.yticks([])  
    plt.show()

class LSystem:
    def __init__(self, axiom, rules):
        self.axiom = axiom
        self.rules = rules
    
    def iterate(self, generations=1):
        output = [self.axiom]
        for i in range(generations):
            last = output[-1]
            output.append(self.apply_rules(last))
        return output
    
    def apply_rules(self, sequence): #sequence list integers
        result = []
        for i in sequence:
            g = self.rules.get(i,i)
            if isinstance(g, list):
                result = result + g
            else:
                result.append(g)
        return result

def evolve_system(initial_state, rules, generations):
    evolution = [initial_state]
    current_state = initial_state

    for _ in range(generations):
        new_state = []
        for category in current_state:
            new_state.extend(rules[category])

        evolution.append(new_state)
        current_state = new_state

    return evolution


# - - - - - MIDI - - - - -


def connect_midi():
    
    axiom = [0, 1, 2, 3, 4, 5, 6]
    # rules = {0:4, 1:[3, 5], 2:[0, 2], 4:0, 5:1} #cannot make plot with these rules
    rules = {0: 4, 1: 3, 2: 6, 3: 5, 4: 2, 5: 1, 6: 0} 
    l_system = LSystem(axiom, rules)

    with mido.open_input() as inport:
        for msg in inport:
            if not msg.is_meta:
                if msg.type == 'control_change':
                    print(msg.value)
                    out = l_system.iterate(generations=1)
                    l_system.axiom = out[-1]
                    for i in out[-1]:
                        msg = mido.Message('note_on', note=i)
                        port = mido.open_output('Driver IAC Bus 1')
                        port.send(msg)
                        time.sleep(0.2)


                    
            
        
    


def main():

    # 1° method: 

    # axiom = [0,1,2,3,4,5,6]
    # # rules = {0:4, 1:[3, 5], 2:[0, 2], 4:0, 5:1} #cannot make plot with these rules
    # rules = {0:4, 1:3, 2:6, 3:5, 4:2, 5:1, 6:0}
    # l_system = LSystem(axiom, rules)
    # out = l_system.iterate(generations=50)
    # print(out)
    # plot_evolution(out)

# - - - 
    # 2° method 

    initial_state = [0, 1, 2, 3]  
    # rules = {                 cannot make plot with these rules
    #     0: [2, 3],
    #     1: [0, 1, 4],
    #     2: [3],
    #     3: [1, 2],
    #     4: [1]
    # }
    rules = {
        0: [2],
        1: [4],
        2: [3],
        3: [1],
        4: [0]
    }
    generations = 15
    evolution_result = evolve_system(initial_state, rules, generations)
    print(evolution_result)
    plot_evolution(evolution_result)


if __name__ == "__main__":
    # main()  # this create the a plot
    connect_midi()
