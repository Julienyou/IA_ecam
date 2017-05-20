# pylos.py
# Author: Elise Raxhon & Julien Beard
# Version: May 19, 2017
# -*- coding: utf-8 -*-

import argparse
import socket
import sys
import json
import copy
import json

from tree import Tree
from lib import game



class PylosState(game.GameState):
    '''Class representing a state for the Pylos game.'''

    def __init__(self, initialstate=None):

        if initialstate == None:
            # define a layer of the board
            def squareMatrix(size):
                matrix = []
                for i in range(size):
                    matrix.append(
                        [None] * size)
                return matrix

            board = []
            for i in range(4):
                board.append(squareMatrix(4 - i))

            initialstate = {
                'board': board,
                'reserve': [15, 15],
                'turn': 0
            }

        super().__init__(initialstate)

    def get(self, layer, row, column):
        """Checks if the position (layer,row,column) is on the board"""
        if layer < 0 or row < 0 or column < 0:
            raise game.InvalidMoveException('The position ({}) is outside of the board'.format([layer, row, column]))
        try:
            return self._state['visible']['board'][layer][row][column]
        except:
            raise game.InvalidMoveException('The position ({}) is outside of the board'.format([layer, row, column]))

    def safeGet(self, layer, row, column):
        try:
            return self.get(layer, row, column)
        except game.InvalidMoveException:
            return None

    def validPosition(self, layer, row, column):
        """Checks if the position is free and stable"""
        if self.get(layer, row, column) != None:
            raise game.InvalidMoveException('The position ({}) is not free'.format([layer, row, column]))

        if layer > 0:
            if (
                self.get(layer - 1, row, column) is None or
                self.get(layer - 1, row + 1, column) is None or
                self.get(layer - 1, row + 1, column + 1) is None or
                self.get(layer - 1, row, column + 1) is None
            ):
                raise game.InvalidMoveException('The position ({}) is not stable'.format([layer, row, column]))

    def canMove(self, layer, row, column):
        if self.get(layer, row, column) is None:
            raise game.InvalidMoveException('The position ({}) is empty'.format([layer, row, column]))

        if layer < 3:
            if (
                self.safeGet(layer + 1, row, column) is not None or
                self.safeGet(layer + 1, row - 1, column) is not None or
                self.safeGet(layer + 1, row - 1, column - 1) is not None or
                self.safeGet(layer + 1, row, column - 1) is not None
            ):
                raise game.InvalidMoveException('The position ({}) is not movable'.format([layer, row, column]))

    def createSquare(self, coord):
        layer, row, column = tuple(coord)

        def isSquare(layer, row, column):
            if (
                self.safeGet(layer, row, column) != None and
                self.safeGet(layer, row + 1, column) == self.safeGet(layer, row, column) and
                self.safeGet(layer, row + 1, column + 1) == self.safeGet(layer, row, column) and
                self.safeGet(layer, row, column + 1) == self.safeGet(layer, row, column)
            ):
                return True
            return False

        if (
            isSquare(layer, row, column) or
            isSquare(layer, row - 1, column) or
            isSquare(layer, row - 1, column - 1) or
            isSquare(layer, row, column - 1)
        ):
            return True
        return False

    def set(self, coord, value):
        """It is called to add a ball on the board"""
        layer, row, column = tuple(coord)
        self.validPosition(layer, row, column)
        self._state['visible']['board'][layer][row][column] = value

    def remove(self, coord, player):
        layer, row, column = tuple(coord)
        self.canMove(layer, row, column)
        sphere = self.get(layer, row, column)
        if sphere != player:
            raise game.InvalidMoveException('not your sphere')
        self._state['visible']['board'][layer][row][column] = None

    def update(self, move, player):
        """update the state with the move and raise game.InvalidMoveException"""
        state = self._state['visible']
        if move['move'] == 'place':
            if state['reserve'][player] < 1:
                raise game.InvalidMoveException('no more sphere')
            self.set(move['to'], player)
            state['reserve'][player] -= 1
        elif move['move'] == 'move':
            if move['to'][0] <= move['from'][0]:
                raise game.InvalidMoveException('you can only move to upper layer')
            sphere = self.remove(move['from'], player)
            try:
                self.set(move['to'], player)
            except game.InvalidMoveException as e:
                self.set(move['from'], player)
                raise e
        else:
            raise game.InvalidMoveException('Invalid Move:\n{}'.format(move))

        if 'remove' in move:
            if not self.createSquare(move['to']):
                raise game.InvalidMoveException('You cannot remove spheres')
            if len(move['remove']) > 2:
                raise game.InvalidMoveException('Can\'t remove more than 2 spheres')
            for coord in move['remove']:
                sphere = self.remove(coord, player)
                state['reserve'][player] += 1
        state['turn'] = (state['turn'] + 1) % 2

    def winner(self):
        """return 0 or 1 if a winner, return None if draw, return -1 if game continue"""
        state = self._state['visible']
        if state['reserve'][0] < 1:
            return 1
        elif state['reserve'][1] < 1:
            return 0
        return -1

    def val2str(self, val):
        return '_' if val == None else '@' if val == 0 else 'O'

    def player2str(self, val):
        return 'Light' if val == 0 else 'Dark'

    def printSquare(self, matrix):
        print(' ' + '_' * (len(matrix) * 2 - 1))
        print('\n'.join(map(lambda row: '|' + '|'.join(map(self.val2str, row)) + '|', matrix)))

    def prettyprint(self):
        """print the state"""
        state = self._state['visible']
        for layer in range(4):
            self.printSquare(state['board'][layer])
            print()

        for player, reserve in enumerate(state['reserve']):
            print('Reserve of {}:'.format(self.player2str(player)))
            print((self.val2str(player) + ' ') * reserve)
            print()

        print('{} to play !'.format(self.player2str(state['turn'])))
        # print(json.dumps(self._state['visible'], indent=4))


class PylosServer(game.GameServer):
    '''Class representing a server for the Pylos game.'''

    def __init__(self, verbose=False):
        super().__init__('Pylos', 2, PylosState(), verbose=verbose)

    def applymove(self, move):
        try:
            self._state.update(json.loads(move), self.currentplayer)
        except json.JSONDecodeError:
            raise game.InvalidMoveException('move must be valid JSON string: {}'.format(move))


class PylosClient(game.GameClient):
    '''Class representing a client for the Pylos game.'''

    def __init__(self, name, server, verbose=False):
        self.deltas = []
        self.firstmoves = []
        super().__init__(server, PylosState, verbose=verbose)
        self.__name = name

    def _handle(self, message):
        pass

    def allplacement(self, test_pylos):
        """Function that returns a list of "move" dictionaries. Contains all the possible ways to place a ball from the
        reserve. Also take into acount the case when a square is made and one or two balls are being removed."""
        placements = []
        player = test_pylos._state['visible']['turn']
        for layer in range(4):
            for row in range(4-layer):
                for column in range(4-layer):
                    value = test_pylos.get(layer,row,column)
                    if value is None:
                        try:
                            test_pylos.validPosition(layer, row, column)
                        except game.InvalidMoveException:
                            pass
                        else:
                            if test_pylos.createSquare((layer, row, column)) is True:
                                if player == 0:
                                    removableballs = self.removableballs0(test_pylos)
                                    removableballs.apppend([layer, row, column])
                                else:
                                    removableballs = self.removableballs1(test_pylos)
                                    removableballs.apppend([layer, row, column])
                                for i in removableballs:
                                    if i[0] == layer - 1 and i[1] == row and i[2] == column:
                                        removableballs.remove(i)
                                    elif i[0] == layer - 1 and i[1] == row + 1 and i[2] == column:
                                        removableballs.remove(i)
                                    elif i[0] == layer - 1 and i[1] == row + 1 and i[2] == column + 1:
                                        removableballs.remove(i)
                                    elif i[0] == layer - 1 and i[1] == row and i[2] == column + 1:
                                        removableballs.remove(i)

                                for i in removableballs:
                                    move = {
                                        'move': 'place',
                                        'to': [layer, row, column],
                                        'remove': i
                                    }

                                    placements.append(move)
                            else:
                                move = {
                                    'move': 'place',
                                    'to': [layer, row, column]
                                }
                                placements.append(move)
        return placements

    def holes(self, test_pylos):
        """Function returning a list of lists [layer, row, column] for all the valid holes of the board"""
        availableholes = []
        for layer in range(1, 4):
            for row in range(4 - layer):
                for column in range(4 - layer):
                    value = test_pylos.get(layer, row, column)
                    if value is None:
                        try:
                            test_pylos.validPosition(layer, row, column)
                            hole = [layer, row, column]
                        except game.InvalidMoveException:
                            pass
                        else:
                            availableholes.append(hole)
        return availableholes

    def removableballs0(self, test_pylos):
        """Function returning a list of lists [layer, row, column] for all the removable balls of the board for player 0"""
        removableballs=[]
        for layer in range(4):
            for row in range(4 - layer):
                for column in range(4 - layer):
                    value = test_pylos.get(layer, row, column)
                    if value == 0:
                        try:
                            test_pylos.canMove(layer, row, column)
                        except game.InvalidMoveException:
                            pass
                        else:
                            coord = [layer, row, column]
                            removableballs.append(coord)
        return removableballs

    def removableballs1(self, test_pylos):
        """Function returning a list of lists [layer, row, column] for all the removable balls of the board for
        player 1"""
        removableballs=[]
        for layer in range(4):
            for row in range(4 - layer):
                for column in range(4 - layer):
                    value = test_pylos.get(layer, row, column)
                    if value == 1:
                        try:
                            test_pylos.canMove(layer, row, column)
                        except game.InvalidMoveException :
                            pass
                        else:
                            coord = [layer, row, column]
                            removableballs.append(coord)
        return removableballs

    def moveup(self, test_pylos):
        """Function returning a list of all the possible dictionaries "move" for moving up a ball, including the case
        when a square is formed and one or two balls are being removed. Two parts : one for player 0 and one for
        player 1"""
        possibilities = []
        if test_pylos._state['visible']['turn'] is 0:
            for layer in range(4):
                for row in range(4 - layer):
                    for column in range(4 - layer):
                        value = test_pylos.get(layer, row, column)
                        if value is 0:
                            try:
                                test_pylos.canMove(layer, row,column)
                            except game.InvalidMoveException:
                                pass
                            # When we know which ball is moving, we can remove some possibilities from the
                            # availableholes list
                            availableholes = self.holes(test_pylos)
                            for i in availableholes:
                                if i[0] <= layer:
                                    availableholes.remove(i)
                                elif i[0] == layer + 1 and i[1] == row and i[2] == column:
                                    availableholes.remove(i)
                                elif i[0] == layer + 1 and i[1] == row + 1 and i[0] == column:
                                    availableholes.remove(i)
                                elif i[0] == layer + 1 and i[1] == row + 1 and i[0] == column + 1:
                                    availableholes.remove(i)
                                elif i[0] == layer + 1 and i[1] == row and i[0] == column + 1:
                                    availableholes.remove(i)

                            for i in availableholes:
                                move = {
                                    'move': 'move',
                                    'from': [layer, row, column],
                                    'to': i
                                }
                                possibilities.append(move)

                            if test_pylos.createSquare((layer, row, column)) is True:
                                removableballs0 = self.removableballs0(test_pylos)
                                for i in removableballs0:
                                    if i[0] == layer - 1 and i[1] == row and i[2] == column:
                                        removableballs0.remove(i)
                                    elif i[0] == layer - 1 and i[1] == row + 1 and i[2] == column:
                                        removableballs0.remove(i)
                                    elif i[0] == layer - 1 and i[1] == row + 1 and i[2] == column + 1:
                                        removableballs0.remove(i)
                                    elif i[0] == layer - 1 and i[1] == row and i[2] == column + 1:
                                        removableballs0.remove(i)
                                    elif i[0] == layer and i[1] == row and i[2] == column:
                                        removableballs0.remove(i)
                                    removableballs0.append(i)
                                removableballs01 = copy.deepcopy(removableballs0)
                                for i in removableballs0:
                                    for j in removableballs01:
                                        if i != j:
                                            removewhat = []
                                            removewhat.append([i, j])
                                            move['remove'] = removewhat
                                        else:
                                            pass
                                possibilities.append(move)

        else:
            for layer in range(4):
                for row in range(4 - layer):
                    for column in range(4 - layer):
                        value = test_pylos.get(layer, row, column)
                        if value is 1:
                            try:
                                test_pylos.canMove(layer, row, column)
                            except game.InvalidMoveException:
                                pass
                            availableholes = self.holes(test_pylos)
                            for i in availableholes:
                                if i[0] <= layer:
                                    availableholes.remove(i)
                                elif i[0] == layer + 1 and i[1] == row and i[2] == column:
                                    availableholes.remove(i)
                                elif i[0] == layer + 1 and i[1] == row + 1 and i[0] == column:
                                    availableholes.remove(i)
                                elif i[0] == layer + 1 and i[1] == row + 1 and i[0] == column + 1:
                                    availableholes.remove(i)
                                elif i[0] == layer + 1 and i[1] == row and i[0] == column + 1:
                                    availableholes.remove(i)

                            for i in availableholes:
                                move = {
                                    'move': 'move',
                                    'from': [layer, row, column],
                                    'to': i
                                }
                            if test_pylos.createSquare((layer, row, column)) is True:
                                removableballs1 = self.removableballs1(test_pylos)
                                for i in removableballs1:
                                    if i[0] == layer - 1 and i[1] == row and i[2] == column:
                                        removableballs1.remove(i)
                                    elif i[0] == layer - 1 and i[1] == row + 1 and i[2] == column:
                                        removableballs1.remove(i)
                                    elif i[0] == layer - 1 and i[1] == row + 1 and i[2] == column + 1:
                                        removableballs1.remove(i)
                                    elif i[0] == layer - 1 and i[1] == row and i[2] == column + 1:
                                        removableballs1.remove(i)
                                    elif i[0] == layer and i[1] == row and i[2] == column:
                                        removableballs1.remove(i)
                                    removableballs1.append(i)
                                removableballs11 = copy.deepcopy(removableballs1)
                                for i in removableballs1:
                                    for j in removableballs11:
                                        if i != j:
                                            removewhat = []
                                            removewhat.append([i, j])
                                            move['remove'] = removewhat
                                        else:
                                            pass
                                possibilities.append(move)
        return possibilities


    def delta_func(self, st):
        """Function calculating the delta of the two players reserves. It also adds a key "number" to the "state"
        dictionary for attributing a number to each of the children of the first iteration. Returning the number
        and de delta."""
        res0 = st._state['visible']['reserve'][0]
        res1 = st._state['visible']['reserve'][1]
        number = st._state['visible']['number']
        if st._state['visible']['turn'] is 0:
            delta = res0-res1
        else:
            delta = res1-res0
        return number, delta

    def firstmoves_func(self, movements):
        """Function returning a list of all the possible movements (place or move up)"""

        self.firstmoves = []
        self.firstmoves.append(movements)
        return self.firstmoves

    def tree(self, st, iter):
        """Function that increses the 'number' value for each child of the first iteration. For the further iterations,
        the 'number' values correspond to the one of the parent."""
        player = st._state['visible']['turn']
        number = st._state['visible']['number']
        #state = Pylos_copy._state['visible']
        placements = self.allplacement(st)
        upmoves = self.moveup(st)
        movements = placements + upmoves
        if iter is 3:
            self.firstmoves_func(movements)
        children = []
        if iter < 1:
            return Tree(st._state['visible'])
        self.deltas = []
        if iter == 3:
            iter -= 1
            for movement in movements:
                Pylos_copy = copy.deepcopy(st)
                number += 1
                Pylos_copy.update(movement, player)
                Pylos_copy._state['visible']['number'] = number
                self.deltas.append(self.delta_func(Pylos_copy))
    #            max_indice = [number for number, delta in self.deltas if delta == max(self.deltas[1])]
    #            Pylos_copy.set(movement['to'],player)
                child = self.tree(Pylos_copy, iter)
                children.append(child)
        else:
            iter -= 1
            for movement in movements:
                Pylos_copy = copy.deepcopy(st)
                Pylos_copy.update(movement, player)
                Pylos_copy._state['visible']['number'] = number
                self.deltas.append(self.delta_func(Pylos_copy))
     #           max_indice = [number for number, delta in self.deltas if delta == max(self.deltas[1])]
                #            Pylos_copy.set(movement['to'],player)
                child = self.tree(Pylos_copy, iter)
                children.append(child)
        return Tree(st._state['visible'], children)

    def mostfrequent(self, L):
        """Returns the most frequent element of the list"""
        L.sort()
        n0, e0 = 0, None
        ep = None
        for e in L:
            if e != ep:
                n = L.count(e)
                if n > n0:
                    n0, e0 = n, e
                ep = e
        return e0, n0

    def _nextmove(self, state):
        '''
        Returning move as a string
        example of moves
        coordinates are like [layer, row, colums]
        move = {
            'move': 'place',
            'to': [0,1,1]
        }

        move = {
            'move': 'move',
            'from': [0,1,1],
            'to': [1,1,1]
        }

        move = {
            'move': 'move',
            'from': [0,1,1],
            'to': [1,1,1]
            'remove': [
                [1,1,1],
                [1,1,2]
            ]
        }

        return it in JSON
        '''

#        if state._state['visible']['reserve'][0] == 15:
#            pylosCopy = PylosState()
#            pylosCopy._state['visible']['number'] = -1
#            print(self.tree(pylosCopy, 3))
#            print(self.firstmoves[0][0])
        print('coucou')
        if state._state['visible']['turn'] == 1:
            print('if ok')
            pylosCopy = copy.deepcopy(state)
            pylosCopy._state['visible']['number'] = -1
            print(self.tree(pylosCopy, 3))
            for i in range(len(self.deltas)):
                print('for ok')
                max_indice = [number for number, delta in self.deltas if delta == max(self.deltas[i])]
            e, n = self.mostfrequent(max_indice)
            print(self.firstmoves[0][0])
            return json.dumps(self.firstmoves[0][0])
            #indice = self.deltas[0]
            #print(self.firstmoves[0][0])

        if state._state['visible']['turn'] == 0:
            for layer in range(4):
                for row in range(4 - layer):
                    for column in range(4 - layer):
                        if state.get(layer, row, column) == None:
                            return json.dumps({
                                'move': 'place',
                                'to': [layer, row, column]
                            })



if __name__ == '__main__':
    # Create the top-level parser
    parser = argparse.ArgumentParser(description='Pylos game')
    subparsers = parser.add_subparsers(description='server client', help='Pylos game components', dest='component')
    # Create the parser for the 'server' subcommand
    server_parser = subparsers.add_parser('server', help='launch a server')
    server_parser.add_argument('--host', help='hostname (default: localhost)', default='localhost')
    server_parser.add_argument('--port', help='port to listen on (default: 5000)', default=5000)
    server_parser.add_argument('--verbose', action='store_true')
    # Create the parser for the 'client' subcommand
    client_parser = subparsers.add_parser('client', help='launch a client')
    client_parser.add_argument('name', help='name of the player')
    client_parser.add_argument('--host', help='hostname of the server (default: localhost)', default='127.0.0.1')
    client_parser.add_argument('--port', help='port of the server (default: 5000)', default=5000)
    client_parser.add_argument('--verbose', action='store_true')
    # Parse the arguments of sys.args
    args = parser.parse_args()
    if args.component == 'server':
        PylosServer(verbose=args.verbose).run()
    else:
        PylosClient(args.name, (args.host, args.port), verbose=args.verbose)