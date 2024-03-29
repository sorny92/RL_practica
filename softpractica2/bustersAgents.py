# bustersAgents.py
# ----------------
# Licensing Information:  You are free to use or extend these projects for
# educational purposes provided that (1) you do not distribute or publish
# solutions, (2) you retain this notice, and (3) you provide clear
# attribution to UC Berkeley.
#
# Attribution Information: The Pacman AI projects were developed at UC Berkeley.
# The core projects and autograders were primarily created by John DeNero
# (denero@cs.berkeley.edu) and Dan Klein (klein@cs.berkeley.edu).
# Student side autograding was added by Brad Miller, Nick Hay, and
# Pieter Abbeel (pabbeel@cs.berkeley.edu).


from pathlib import Path
import sys
import random
from distanceCalculator import Distancer
from game import Actions
import util
import os
import os.path
import numpy as np
from game import Agent
from game import Directions
from keyboardAgents import KeyboardAgent
import inference
import busters


class NullGraphics:
    "Placeholder for graphics"

    def initialize(self, state, isBlue=False):
        pass

    def update(self, state):
        pass

    def pause(self):
        pass

    def draw(self, state):
        pass

    def updateDistributions(self, dist):
        pass

    def finish(self):
        pass


class KeyboardInference(inference.InferenceModule):
    """
    Basic inference module for use with the keyboard.
    """

    def initializeUniformly(self, gameState):
        "Begin with a uniform distribution over ghost positions."
        self.beliefs = util.Counter()
        for p in self.legalPositions:
            self.beliefs[p] = 1.0
        self.beliefs.normalize()

    def observe(self, observation, gameState):
        noisyDistance = observation
        emissionModel = busters.getObservationDistribution(noisyDistance)
        pacmanPosition = gameState.getPacmanPosition()
        allPossible = util.Counter()
        for p in self.legalPositions:
            trueDistance = util.manhattanDistance(p, pacmanPosition)
            if emissionModel[trueDistance] > 0:
                allPossible[p] = 1.0
        allPossible.normalize()
        self.beliefs = allPossible

    def elapseTime(self, gameState):
        pass

    def getBeliefDistribution(self):
        return self.beliefs


class BustersAgent:
    "An agent that tracks and displays its beliefs about ghost positions."

    def __init__(self, index=0, inference="ExactInference", ghostAgents=None,
                 observeEnable=True, elapseTimeEnable=True):
        inferenceType = util.lookup(inference, globals())
        self.inferenceModules = [inferenceType(a) for a in ghostAgents]
        self.observeEnable = observeEnable
        self.elapseTimeEnable = elapseTimeEnable

    def registerInitialState(self, gameState):
        "Initializes beliefs and inference modules"
        import __main__
        self.display = __main__._display
        for inference in self.inferenceModules:
            inference.initialize(gameState)
        self.ghostBeliefs = [inf.getBeliefDistribution() for inf in self.inferenceModules]
        self.firstMove = True

    def observationFunction(self, gameState):
        "Removes the ghost states from the gameState"
        agents = gameState.data.agentStates
        gameState.data.agentStates = [agents[0]] + [None for i in range(1, len(agents))]
        return gameState

    def getAction(self, gameState):
        "Updates beliefs, then chooses an action based on updated beliefs."
        # for index, inf in enumerate(self.inferenceModules):
        #    if not self.firstMove and self.elapseTimeEnable:
        #        inf.elapseTime(gameState)
        #    self.firstMove = False
        #    if self.observeEnable:
        #        inf.observeState(gameState)
        #    self.ghostBeliefs[index] = inf.getBeliefDistribution()
        # self.display.updateDistributions(self.ghostBeliefs)
        return self.chooseAction(gameState)

    def chooseAction(self, gameState):
        "By default, a BustersAgent just stops.  This should be overridden."
        return Directions.STOP


class BustersKeyboardAgent(BustersAgent, KeyboardAgent):
    "An agent controlled by the keyboard that displays beliefs about ghost positions."

    def __init__(self, index=0, inference="KeyboardInference", ghostAgents=None):
        KeyboardAgent.__init__(self, index)
        BustersAgent.__init__(self, index, inference, ghostAgents)

    def getAction(self, gameState):
        return BustersAgent.getAction(self, gameState)

    def chooseAction(self, gameState):
        return KeyboardAgent.getAction(self, gameState)


'''Random PacMan Agent'''


class RandomPAgent(BustersAgent):

    def registerInitialState(self, gameState):
        BustersAgent.registerInitialState(self, gameState)
        self.distancer = Distancer(gameState.data.layout, False)

    ''' Example of counting something'''

    def countFood(self, gameState):
        food = 0
        for width in gameState.data.food:
            for height in width:
                if (height == True):
                    food = food + 1
        return food

    ''' Print the layout'''

    def printGrid(self, gameState):
        table = ""
        # print(gameState.data.layout) ## Print by terminal
        for x in range(gameState.data.layout.width):
            for y in range(gameState.data.layout.height):
                food, walls = gameState.data.food, gameState.data.layout.walls
                table = table + gameState.data._foodWallStr(food[x][y], walls[x][y]) + ","
        table = table[:-1]
        return table

    def chooseAction(self, gameState):
        move = Directions.STOP
        legal = gameState.getLegalActions(0)  # Legal position from the pacman
        move_random = random.randint(0, 3)
        if (move_random == 0) and Directions.WEST in legal:
            move = Directions.WEST
        if (move_random == 1) and Directions.EAST in legal:
            move = Directions.EAST
        if (move_random == 2) and Directions.NORTH in legal:
            move = Directions.NORTH
        if (move_random == 3) and Directions.SOUTH in legal:
            move = Directions.SOUTH
        return move


class GreedyBustersAgent(BustersAgent):
    "An agent that charges the closest ghost."

    def registerInitialState(self, gameState):
        "Pre-computes the distance between every two points."
        BustersAgent.registerInitialState(self, gameState)
        self.distancer = Distancer(gameState.data.layout, False)

    def chooseAction(self, gameState):
        """
        First computes the most likely position of each ghost that has
        not yet been captured, then chooses an action that brings
        Pacman closer to the closest ghost (according to mazeDistance!).

        To find the mazeDistance between any two positions, use:
          self.distancer.getDistance(pos1, pos2)

        To find the successor position of a position after an action:
          successorPosition = Actions.getSuccessor(position, action)

        livingGhostPositionDistributions, defined below, is a list of
        util.Counter objects equal to the position belief
        distributions for each of the ghosts that are still alive.  It
        is defined based on (these are implementation details about
        which you need not be concerned):

          1) gameState.getLivingGhosts(), a list of booleans, one for each
             agent, indicating whether or not the agent is alive.  Note
             that pacman is always agent 0, so the ghosts are agents 1,
             onwards (just as before).

          2) self.ghostBeliefs, the list of belief distributions for each
             of the ghosts (including ghosts that are not alive).  The
             indices into this list should be 1 less than indices into the
             gameState.getLivingGhosts() list.
        """
        pacmanPosition = gameState.getPacmanPosition()
        legal = [a for a in gameState.getLegalPacmanActions()]
        livingGhosts = gameState.getLivingGhosts()
        livingGhostPositionDistributions = \
            [beliefs for i, beliefs in enumerate(self.ghostBeliefs)
             if livingGhosts[i + 1]]
        return Directions.EAST


class RLAgent(BustersAgent):
    actions = {
        'North': 0,
        'South': 1,
        'East': 2,
        'West': 3,
        'Stop': 4
    }
    directions = {
        'N': 0,
        'NE': 1,
        'E': 2,
        'SE': 3,
        'S': 4,
        'SW': 5,
        'W': 6,
        'NW': 7,
    }

    game_duration = 0
    episode = 0

    def get_row_qtable(self, closest_ghost_direction, closest_ghost_action, has_wall: int):
        return self.actions[closest_ghost_action] * len(self.actions) + self.directions[closest_ghost_direction] + (
                has_wall * len(self.actions) * len(self.directions))

    def registerInitialState(self, gameState):
        BustersAgent.registerInitialState(self, gameState)
        self.distancer = Distancer(gameState.data.layout, False)

        self.nRowsQTable = len(self.actions) * len(self.directions) * 2
        # alpha    - learning rate
        # epsilon  - exploration rate
        # gamma    - discount factor
        self.alpha = 0.2
        self.gamma = 0.8
        self.epsilon = 0.6
        ##########################################################################
        self.nColumnsQTable = 5

        self.table_file = Path("qtable.txt")
        self.q_table = self.readQtable() or self.initQtable()

    ''' Example of counting something'''

    def countFood(self, gameState):
        food = 0
        for width in gameState.data.food:
            for height in width:
                if height:
                    food = food + 1
        return food

    def printInfo(self, gameState):
        # Dimensiones del mapa
        width, height = gameState.data.layout.width, gameState.data.layout.height
        print("\tWidth: ", width, " Height: ", height)
        # Posicion del Pacman
        print("\tPacman position: ", gameState.getPacmanPosition())
        # Acciones legales de pacman en la posicion actual
        print("\tLegal actions: ", gameState.getLegalPacmanActions())
        # Direccion de pacman
        print("\tPacman direction: ", gameState.data.agentStates[0].getDirection())
        # Numero de fantasmas
        print("\tNumber of ghosts: ", gameState.getNumAgents() - 1)
        # Fantasmas que estan vivos (el indice 0 del array que se devuelve
        # corresponde a pacman y siempre es false)
        print("\tLiving ghosts: ", gameState.getLivingGhosts()[1:])
        # Posicion de los fantasmas
        print("\tGhosts positions: ", gameState.getGhostPositions())
        # Direciones de los fantasmas
        print(
            "\tGhosts directions: ", [
                gameState.getGhostDirections().get(i) for i in range(
                    0, gameState.getNumAgents() - 1)])
        # Distancia de manhattan a los fantasmas
        print("\tGhosts distances: ", gameState.data.ghostDistances)
        # Puntos de comida restantes
        print("\tPac dots: ", gameState.getNumFood())
        # Distancia de manhattan a la comida mas cercada
        print("\tDistance nearest pac dots: ", gameState.getDistanceNearestFood())
        # Paredes del mapa
        print("\tMap Walls:  \n", gameState.getWalls())
        # Comida en el mapa
        print("\tMap Food:  \n", gameState.data.food)
        # Estado terminal
        print("\tGana el juego: ", gameState.isWin())
        # Puntuacion
        print("\tScore: ", gameState.getScore())

    def initQtable(self):
        "Initialize qtable"
        return (np.zeros((self.nRowsQTable, self.nColumnsQTable)).tolist())

    def readQtable(self):
        "Read qtable from disc"
        if not self.table_file.is_file():
            return None

        content = self.table_file.read_text()

        if content == '':
            return None

        q_table = []

        for line in content.split('\n')[:-1]:
            values = [float(x) for x in line.split()]
            q_table.append(values)

        return q_table

    def writeQtable(self):
        "Write qtable to disc"
        with open(self.table_file, 'w') as f:
            for line in self.q_table:
                for item in line:
                    f.write(str(item) + " ")
                f.write("\n")

    def get_closest_ghost(self, gameState):
        closest_ghost_idx = 0
        lowest = 1000
        for idx, g in enumerate(gameState.data.ghostDistances):
            if g is None or g > lowest:
                continue
            else:
                lowest = g
                closest_ghost_idx = idx
        return closest_ghost_idx

    def computePosition(self, state):
        """
        Compute the row of the qtable for a given state.
        """
        pacman_position = state.getPacmanPosition()

        closest_ghost_idx = self.get_closest_ghost(state)
        position_closest_ghost = state.getGhostPositions()[closest_ghost_idx]
        if not len(state.getGhostDirections()):
            action_closest_ghost = "Stop"
        else:
            action_closest_ghost = state.getGhostDirections()[closest_ghost_idx]
        distance_v = (
            position_closest_ghost[0] - pacman_position[0] + 0.0001, position_closest_ghost[1] - pacman_position[1])
        angle = np.arctan(distance_v[1] / distance_v[0])
        n_directions = 2
        ghost_direction = round(2 * angle * n_directions / np.pi)
        wall_check = None
        if distance_v[1] >= 0 and distance_v[0] >= 0:
            if ghost_direction == 0:
                ghost_direction = "E"
                wall_check = [1, 0]
            elif ghost_direction == 1:
                ghost_direction = "NE"
                wall_check = [1, 1]
            elif ghost_direction == 2:
                ghost_direction = "N"
                wall_check = [0, 1]
        if distance_v[1] >= 0 > distance_v[0]:
            if ghost_direction == 2 or ghost_direction == -2:
                ghost_direction = "N"
                wall_check = [0, 1]
            elif ghost_direction == -1:
                ghost_direction = "NW"
                wall_check = [-1, 1]
            elif ghost_direction == 0:
                ghost_direction = "W"
                wall_check = [-1, 0]
        if distance_v[1] < 0 <= distance_v[0]:
            if ghost_direction == 0:
                ghost_direction = "E"
                wall_check = [1, 0]
            elif ghost_direction == -1:
                ghost_direction = "SE"
                wall_check = [1, -1]
            elif ghost_direction == -2:
                ghost_direction = "S"
                wall_check = [0, -1]
        if distance_v[1] < 0 and distance_v[0] < 0:
            if ghost_direction == 2 or ghost_direction == -2:
                ghost_direction = "S"
                wall_check = [0, -1]
            elif ghost_direction == 1:
                ghost_direction = "SW"
                wall_check = [-1, -1]
            elif ghost_direction == 0:
                ghost_direction = "W"
                wall_check = [-1, 0]

        has_wall = state.hasWall(pacman_position[0] + wall_check[0],
                                 pacman_position[1] + wall_check[1])
        print(has_wall, ghost_direction, action_closest_ghost)
        return self.get_row_qtable(ghost_direction, action_closest_ghost, has_wall)

    def getQValue(self, state, action):
        """
          Returns Q(state,action)
          Should return 0.0 if we have never seen a state
          or the Q node value otherwise
        """
        position = self.computePosition(state)
        action_column = self.actions[action]

        return self.q_table[position][action_column]

    def computeValueFromQValues(self, state):
        """
          Returns max_action Q(state,action)
          where the max is over legal actions.  Note that if
          there are no legal actions, which is the case at the
          terminal state, you should return a value of 0.0.
        """
        legalActions = state.getLegalActions(0)
        if len(legalActions) == 0:
            return 0
        return max(self.q_table[self.computePosition(state)])

    def computeActionFromQValues(self, state):
        """
          Compute the best action to take in a state.  Note that if there
          are no legal actions, which is the case at the terminal state,
          you should return None.
        """
        legalActions = state.getLegalActions(0)
        if len(legalActions) == 0:
            return None

        best_actions = [legalActions[0]]
        best_value = self.getQValue(state, legalActions[0])
        for action in legalActions:
            value = self.getQValue(state, action)
            if value == best_value:
                best_actions.append(action)
            if value > best_value:
                best_actions = [action]
                best_value = value

        return random.choice(best_actions)

    def getAction(self, state):
        """
          Compute the action to take in the current state.  With
          probability self.epsilon, we should take a random action and
          take the best policy action otherwise.  Note that if there are
          no legal actions, which is the case at the terminal state, you
          should choose None as the action.
        """
        legalActions = state.getLegalActions(0)
        action = None

        if len(legalActions) == 0:
            return action

        flip = util.flipCoin(self.epsilon)

        if flip:
            return random.choice(legalActions)
        return self.getPolicy(state)

    def getReward(self, state, nextState):
        """
          Return a reward value based on the information of state and nextState
        """
        reward = -1

        # The closer to the closest ghost the better? Maybe it's good for the policy? But might get stuck in walls
        # closest_ghost_idx = self.get_closest_ghost(state)
        # reward += max(10 - state.data.ghostDistances[closest_ghost_idx], 0)

        # If eats a ghost that's good
        if state.get_n_living_ghosts() != nextState.get_n_living_ghosts():
            reward += 400

        # If win the game many points
        # if nextState.isWin():
        #    reward += 1000
        return reward

    def logging_score(self, filename, episode, game_score, game_duration):
        with open(filename, 'a') as f:
            f.write(f"{episode},{game_score},{game_duration}\n")

    def update(self, state, action, nextState, reward):
        """
          The parent class calls this to observe a
          state = action => nextState and reward transition.
          You should do your Q-Value update here
        """
        print("Started in state:")
        # self.printInfo(state)
        print("Took action: ", action)
        print("Ended in state:")
        # self.printInfo(nextState)
        print("Got reward: ", reward)
        print("---------------------------------")
        self.game_duration += 1

        s_row = self.computePosition(state)
        action_v = self.actions[action]
        old_q_value = self.q_table[s_row][action_v]
        unlearning = (1 - self.alpha)

        if nextState.isWin():
            self.q_table[s_row][action_v] = unlearning * old_q_value + (self.alpha * reward)
            # If a terminal state is reached
            self.writeQtable()
            self.episode += 1
            self.logging_score("lab1_wallawareness.txt", self.episode, nextState.getScore(), self.game_duration)
            self.game_duration = 0
        else:
            q_value_next_state = self.computeValueFromQValues(nextState)
            self.q_table[s_row][action_v] = unlearning * old_q_value + self.alpha * (
                    reward + self.gamma * q_value_next_state)

    def getPolicy(self, state):
        "Return the best action in the qtable for a given state"
        return self.computeActionFromQValues(state)

    def getValue(self, state):
        "Return the highest q value for a given state"
        return self.computeValueFromQValues(state)
