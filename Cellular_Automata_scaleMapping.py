# CA rules Elementary Cellular automaton
# 1D, 8bit computation

import numpy as np
import mido
import time


class CA:
    
    def __init__(self, rule):
        self.rule = rule

    @staticmethod
    def decimal_to_binary_list(decimal_number):
        if 0 <= decimal_number <= 255:
            binary_representation = bin(decimal_number)[2:]
            binary_representation = binary_representation.zfill(8)
            binary_list = [int(bit) for bit in binary_representation]

            return binary_list
        else:
            print("Number must be between 0 and 255.")
            return None

    @staticmethod
    def binary_list_index(binary_sequence):  # e.g. binary_sequence = [1, 0, 1]
        if len(binary_sequence) == 3:
            binary_string = ''.join(map(str, binary_sequence)).zfill(3)
            decimal_number = int(binary_string, 2)
            return decimal_number
        else:
            print("sequence must contain 3 elements.")
            return None

    @staticmethod
    def binary_from_midi_list(input_list):  # list of one or more midi pitches
        result_list = [0] * 128
        for index in input_list:
            if 0 <= index < 128:
                result_list[index] = 1

        return result_list

    def next_step(self, sequence):   # list of 128 binary digits
        nextSequence = [0]
        binary_rule = list(reversed(self.decimal_to_binary_list(self.rule)))
        for i in range(1, len(sequence)-1):
            triplet = [sequence[i-1], sequence[i], sequence[i+1]]
            binary_index = self.binary_list_index(triplet)
            nextSequence.append(binary_rule[binary_index])
        nextSequence.append(0)
        return nextSequence

    def midiConversion(self, sequence, nextSequence = None):
        midiSeq = []
        if nextSequence == None:
            for i in range(0, len(sequence)):
                if sequence[i] == 1:
                    midiSeq.append(mido.Message("note_on", note= i, velocity=100))
        else:
            for i in range(0, len(sequence)):
                if nextSequence[i] == 1 and sequence[i] == 0:
                    midiSeq.append(mido.Message("note_on", note= i, velocity=100))
                elif (nextSequence[i] == 0 and sequence[i] == 1) or (nextSequence[i] == 1 and sequence[i] == 1):
                    midiSeq.append(mido.Message("note_off", note=i, velocity=0))
        return midiSeq


def main():
    ca = CA(54)
    midiSeq = []
    step = ca.binary_from_midi_list([int(np.random.rand()*127)])
    midiSeq.append(ca.midiConversion(step))
    for _ in range (80):
        next_step = ca.next_step(step)
        midiSeq.append(ca.midiConversion(step, next_step))
        step = next_step
    # step1 = ca.next_step(step0)
    # midiSeq.append(ca.midiConversion(step0, step1))
    # step2 = ca.next_step(step1)
    # midiSeq.append(ca.midiConversion(step1, step2))
    # step3 = ca.next_step(step2)
    # midiSeq.append(ca.midiConversion(step2, step3))

    melody = midiSeq
    # play
    port = mido.open_output('Driver IAC Bus 2')
    for i in melody:
        for j in i:
            port.send(j)
            # if i.type == "note_on":
                # time.sleep(i.time * 60 / self.bpm)
        time.sleep(0.2)


if __name__ == "__main__":
    main()
