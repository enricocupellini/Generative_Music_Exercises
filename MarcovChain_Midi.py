import numpy as np
import mido
from enum import Enum
import time, math

# MIDI input
#note-in, note-out -> must be monophonic sequences
# CTL-in 0 0 0 (value, ctl, channel) start new learning from incoming midi
# CTL-in 0 1 0                      stop learning
# CTL-in n 0 0 (value, ctl, channel) stop learning & start new melody generation of "n" measures
# CTL-in n 1 0 (value(1-127), ctl, channel) set BPM from 0 to 127
# CTL-in n 2 0 (value(0-127), ctl, channel) set BPM from 128 to 255
# CTL-in n m 1 (value(0-127), ctl, channel) set meter (e.g. 4 / 4)

# ASSUMPTIONS:
    # train is made by incoming proposed melody
    # initial probabilties is equal to the first meter position probabilties

# todo & known bugs : 
    # not handle pauses
    # first note have to consider beat positions other than first  
    # meter[1] is unused (beat is always 1/4 )
    # **BEWARE** the kind algorithm I used can lead to missing outputs (0 percentage) regarding to the input


class ProbabilityMatrix:
    def __init__(self, states):
        '''
        states = LIST with all of possible configurations my category can have
        CATEGORY = it can be a SINGLE element like an integer or string (e.g. pitch, duration, beat position)
                          or a TUPLE   (e.g.(pitch, duration))
        '''
        self.states = states
        self.initial_probabilities = np.zeros(len(states))

class MarcovChain:
    def __init__(self, bpm = 60, meter = (4, 4)):
        self.bpm = bpm
        self.meter = meter
        self.midistream = []
        self.learn = False
        self.polyphony = {0:""} #pitch classes and occurrence time
        self.pitchMatrix = np.zeros((self.meter[0], 128, 128)) # transition matrix for all midi pitches X number of pulsations
        self.roundedBeatFractions = [0.1, 0.125, 0.25, 0.334, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4] # Possible beat fractions
        self.durationMatrix = np.zeros((self.meter[0], len(self.roundedBeatFractions), len(self.roundedBeatFractions)))  # smallest category is the noise threshold

    def handleQuarterLength(self, sec):
        beatValue = 60.0/sec    # 60000.0/msec
        beatFraction = self.bpm / beatValue
        # find closest category
        closestCategory = min(self.roundedBeatFractions, key=lambda x: abs(x - beatFraction))   # https://stackoverflow.com/questions/42485098/round-a-number-to-a-given-set-of-values
        return closestCategory
    
    def handleElapsedTime(self, note: mido.Message):
        now = time.time()
        previousTime = self.polyphony[note.note]
        durationSec = now - previousTime
        closestCategory = self.handleQuarterLength(durationSec)
        if closestCategory > 0.1:   # noise threshold
            note.time = closestCategory
            self.midistream.append(note)
            self.polyphony[note.note] = now

        
    def handleMidiStream(self, note: mido.Message):
        if note.type == 'note_on':
            if self.polyphony.get(note.note) is not None:  #note ON before note OFF (wrong melody) -> 
                self.handleElapsedTime(note)
            else:                                       # right event sequence
                self.polyphony[note.note] = time.time() 
        elif note.type == 'note_off':
            end = time.time()
            if self.polyphony.get(note.note) is not None:
                self.handleElapsedTime(note)
        

    def makeMatrices(self):
        self.beatCount = 0
        for i in range(0, len(self.midistream[:-1])):
            msg = self.midistream[i]
            msgNext = self.midistream[i+1]
            meterPosition = math.trunc((self.beatCount) % self.meter[0])
            self.pitchMatrix[meterPosition, msg.note, msgNext.note] +=1
            self.durationMatrix[meterPosition, self.roundedBeatFractions.index(msg.time), self.roundedBeatFractions.index(msgNext.time)] +=1
            self.beatCount += msg.time
        #normalise
        dictSumPitch = {}
        dictSumDuration = {}
        for i in range(0, self.meter[0]):
            dictSumPitch[i] = self.pitchMatrix[i].sum(axis=1)
            dictSumDuration[i] = self.durationMatrix[i].sum(axis=1)
            with np.errstate(divide="ignore", invalid="ignore"):
                self.pitchMatrix[i] = np.where(
                    dictSumPitch[i][:, None],  # Condition: Check each row's sum.
                    # True case: Normalize if sum is not zero.
                    self.pitchMatrix[i] / dictSumPitch[i][:, None],
                    0,  # False case: Keep as zero if sum is zero.
                )
            with np.errstate(divide="ignore", invalid="ignore"):
                self.durationMatrix[i] = np.where(
                    dictSumDuration[i][:, None],  # Condition: Check each row's sum.
                    # True case: Normalize if sum is not zero.
                    self.durationMatrix[i] / dictSumDuration[i][:, None],
                    0,  # False case: Keep as zero if sum is zero.
                )
    
    def _generate_first_message(self):
        pitch = np.random.choice(
            np.arange(0, 128),
            p=self.pitchMatrix[0].sum(axis= 0)/np.sum(self.pitchMatrix[0].sum(axis= 0)),
        )
        duration = np.random.choice(
            self.roundedBeatFractions,
            p=self.durationMatrix[0].sum(axis= 0)/np.sum(self.durationMatrix[0].sum(axis= 0)),
        )
        self.beatCount += duration
        return mido.Message('note_on', note=pitch, velocity=100, time=duration)
    
    def _generate_next_message(self, current_message:mido.Message = None):
        # if not isinstance(current_message, mido.Message): # should be only the first note
        
        pitch = current_message.note
        duration = current_message.time
       
        p00 = self.pitchMatrix[int(self.beatCount) % self.meter[0]][pitch]
        if np.sum(p00) != 1:
            for i in range (0, self.meter[0]):
                p00 = self.pitchMatrix[i][pitch]
                if np.sum(p00) == 1:
                    break
        if np.sum(p00) != 1:
            print(p00)
            return self._generate_first_message()
        nextPitch = np.random.choice(
                np.arange(0, 128),
                p=p00,
            )
        
        p01 = self.durationMatrix[int(self.beatCount) % self.meter[0]][self.roundedBeatFractions.index(duration)]
        if np.sum(p01) != 1:
            for i in range (0, self.meter[0]):
                p01 = self.durationMatrix[i][self.roundedBeatFractions.index(duration)]
                if np.sum(p01) == 1:
                    break
        if np.sum(p01) != 1:
            print(p01)
            return self._generate_first_message()
        nextDuration = np.random.choice(
                self.roundedBeatFractions,
                p = p01
            )
        self.beatCount += nextDuration
        return mido.Message('note_on', note=nextPitch, velocity=100, time=nextDuration)


    def generateMelody(self, measures):
        self.beatCount = 0
        melody = []
        firstNote = self._generate_first_message()
        melody.append(firstNote)
        while self.beatCount < measures * self.meter[0]:
            note = self._generate_next_message(melody[-1])
            noteOff = mido.Message('note_off', note=melody[-1].note)
            melody.append(noteOff)
            melody.append(note)
        melody.append(mido.Message('note_off', note=melody[-1].note))
        
        #play
        for i in melody:
            port = mido.open_output('Driver IAC Bus 2')
            port.send(i)
            if i.type == "note_on":
                time.sleep(i.time * 60 / self.bpm)
        

    
    def getMidi(self, msg):
        if not msg.is_meta:
            # print(msg)
            if (msg.type == 'note_on' or msg.type == 'note_off') and self.learn == True:
                self.handleMidiStream(msg)
            if msg.type == 'control_change':
                if msg.control == 0 and msg.value == 0 and msg.channel == 0:    #start LEARN
                    self.learn = True
                    self.midistream = []
                elif msg.value == 0 and msg.control == 1 and msg.channel == 0:  # stop LEARN
                    self.learn = False
                elif msg.value > 0 and msg.control == 0 and msg.channel == 0: # stop LEARN and generate melody
                    self.makeMatrices()
                    self.generateMelody(msg.value)
                elif msg.value > 0 and msg.control == 1 and msg.channel == 0: #BPM
                    self.bpm = msg.value
                elif msg.value > 0 and msg.control == 2 and msg.channel == 0: #BPM
                    self.bpm = msg.value + 128
                elif msg.value > 0 and msg.control > 0 and msg.channel == 1: #meter
                    self.meter = (msg.value, msg.control)

            

def main():
   
    marcov = MarcovChain()
    with mido.open_input() as inport:
        for msg in inport:
            perfMessage = marcov.getMidi(msg)

if __name__ == "__main__":
    main()