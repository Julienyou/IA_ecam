#!/usr/bin/env python3
# pylos.py
# Author: Quentin Lurkin
# Version: April 28, 2017
# -*- coding: utf-8 -*-

import argparse
import socket
import sys
import json
import copy
import json

from lib import game

class PylosState(game.GameState):
    '''Class representing a state for the Pylos game.'''
    def __init__(self, initialstate=None):

        if initialstate == None:
            # define a layer of the board
            def squareMatrix(size):
                matrix = []
                for i in range(size):
                    matrix.append([None]*size)   #None signifie qu'il n'y a rien donc sur le plateau on met tout à none au debut
                return matrix

            board = []
            for i in range(4):
                board.append(squareMatrix(4-i))

            initialstate = {            #initialise le jeu
                'board': board,
                'reserve': [15, 15],
                'turn': 0
            }

        super().__init__(initialstate)

    def get(self, layer, row, column): #regarde si on sait mettre une bille sur le plateau si elle correspond au dimension etc ...
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
        if self.get(layer, row, column) != None:     # il regarde dans la liste si la valeur est different de none ce qui signifierait qu'il y a deja une bille sur la position
            raise game.InvalidMoveException('The position ({}) is not free'.format([layer, row, column]))

        if layer > 0:   # si il y a une bille qui manque donc qu'on essaie de monter une bille sur 3 billes il dit que c'est pas stable et provoque une erreur
            if (
                self.get(layer-1, row, column) == None or
                self.get(layer-1, row+1, column) == None or
                self.get(layer-1, row+1, column+1) == None or
                self.get(layer-1, row, column+1) == None
            ):
                raise game.InvalidMoveException('The position ({}) is not stable'.format([layer, row, column]))

    def canMove(self, layer, row, column):                     #regarde si la bille peut bouger
        if self.get(layer, row, column) == None:               #impossible car none donc il y a pas de bille
            raise game.InvalidMoveException('The position ({}) is empty'.format([layer, row, column]))

        if layer < 3:                   #regarde si il y a quelque chose au dessus
            if (
                self.safeGet(layer+1, row, column) != None or
                self.safeGet(layer+1, row-1, column) != None or
                self.safeGet(layer+1, row-1, column-1) != None or
                self.safeGet(layer+1, row, column-1) != None
            ):
                raise game.InvalidMoveException('The position ({}) is not movable'.format([layer, row, column]))

    def createSquare(self, coord):
        layer, row, column = tuple(coord)

        def isSquare(layer, row, column):                            #regarde si il y a un carre autour d'une bille
            if (
                self.safeGet(layer, row, column) != None and
                self.safeGet(layer, row+1, column) == self.safeGet(layer, row, column) and
                self.safeGet(layer, row+1, column+1) == self.safeGet(layer, row, column) and
                self.safeGet(layer, row, column+1) == self.safeGet(layer, row, column)
            ):
                return True
            return False

        if (                                                  #regarde les differents elements qui sont juste a cote pour voir si il y a un carre
            isSquare(layer, row, column) or
            isSquare(layer, row-1, column) or
            isSquare(layer, row-1, column-1) or
            isSquare(layer, row, column-1)
        ):
            return True
        return False

    def set(self, coord, value):                    #met la bille
        layer, row, column = tuple(coord)
        self.validPosition(layer, row, column)
        self._state['visible']['board'][layer][row][column] = value

    def remove(self, coord, player):               #enleve la bille
        layer, row, column = tuple(coord)
        self.canMove(layer, row, column)
        sphere = self.get(layer, row, column)
        if sphere != player:
            raise game.InvalidMoveException('not your sphere')
        self._state['visible']['board'][layer][row][column] = None
        
    # update the state with the move
    # raise game.InvalidMoveException
    def update(self, move, player):                    #fais un etat du jeu, enleve la bille dans la reserve,et fais jouer l'autre joueur
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


    # return 0 or 1 if a winner, return None if draw, return -1 if game continue
    def winner(self):
        state = self._state['visible']
        if state['reserve'][0] < 1:               #si le player 0 n'a plus de boules -> 1 gagne
            return 1
        elif state['reserve'][1] < 1:             #si l'autre n'a plus de boules -> 0 gagne
            return 0
        return -1

    def val2str(self, val):                                              #affichage
        return '_' if val == None else '@' if val == 0 else 'O'

    def player2str(self, val):
        return 'Light' if val == 0 else 'Dark'

    def printSquare(self, matrix):
        print(' ' + '_'*(len(matrix)*2-1))
        print('\n'.join(map(lambda row : '|' + '|'.join(map(self.val2str, row)) + '|', matrix)))

    # print the state
    def prettyprint(self):
        state = self._state['visible']
        for layer in range(4):
            self.printSquare(state['board'][layer])
            print()
        
        for player, reserve in enumerate(state['reserve']):
            print('Reserve of {}:'.format(self.player2str(player)))
            print((self.val2str(player)+' ')*reserve)
            print()
        
        print('{} to play !'.format(self.player2str(state['turn'])))
        #print(json.dumps(self._state['visible'], indent=4))       

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
        super().__init__(server, PylosState, verbose=verbose)
        self.__name = name
    
    def _handle(self, message):
        pass
    
    #return move as string
    def _nextmove(self, state):

        '''
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
        if state._state['visible']['reserve'][1] == 15:
            iteration = 2
            t = Tree(state,0,iteration)
            #print(t)

        print(state._state['visible'])

        for layer in range(4):
            for row in range(4-layer):
                for column in range(4-layer):
                    if state.get(layer, row, column) == None:
                        return json.dumps({
                            'move': 'place',
                            'to': [layer, row, column]
                        })

class Tree:
    def __init__(self, state, player, iteration, children=[], move = 'place'):
        self.move = move
        self.__children = copy.deepcopy(children)
        self.__state = state
        self.player = player
        self.iteration = iteration

        bouh = self.tree(self.__state,self.player,self.iteration)

    @property
    def children(self):
        return copy.deepcopy(self.__children)

    def addChild(self, tree):
        self.__children.append(tree)

    def __getitem__(self, index):
        return self.__children[index]

    def __str__(self):
        def _str(tree, level):
            result = '[{}]\ n'.format(tree.__value)
            for child in tree.children:
                result += '{} | - -{} '.format(' ' *level, _str(child, level + 1))
            return result
        return _str(self, 0)

    def savetree(self):
        """Save tree to the 'tree.json' file."""
        try:
            with open('tree.json', 'w') as file:
                file.write(json.dumps({'tree': self.__children}))
        except IOError:
            print("Erreur d'entrée/sortie")


#    def loadcomments(self):
#        """Load comments database from the 'db.json' file."""
#        try:
#            with open('db.json', 'r') as file:
#                content = json.loads(file.read())
#                return content['comments']
#        except:
#            cherrypy.log('Loading database failed.')
#            return []

    def tree(self,state,player, iteration,move = 'place'):
        statecopy = copy.deepcopy(state)
        t = statecopy._state['visible']
        #import ctypes
        #print(ctypes.cast(id(Tree(state, 0, iteration)), ctypes.py_object).value)
        if iteration > 0:
            if move == 'place' and player == 0 :
                for layer in range(0,len(t['board'])):
                    for row in range(0,len(t['board'][layer])):
                        for column in range(0,len(t['board'][layer][row])):
                            for value in t['board'][layer][row]:
                                if value == None:
                                    t['board'][layer][row][column] = 0
                                    iteration -= 1
                                    self.addChild(Tree(statecopy,1,iteration))

            if move == 'place' and player == 1:
                for layer in range(0,len(t['board'])):
                    for row in range(0,len(t['board'][layer])):
                        for column in range(0,len(t['board'][layer][row])):
                            for value in t['board'][layer][row]:
                                if value == None:
                                    t['board'][layer][row][column] = 1
                                    iteration -= 1
                                    self.addChild(Tree(statecopy, 0, iteration))

        arbre = {}
        arbre['tree'] = self.__children
        #print(arbre)
#            if move == 'place' and player == 1 :
#                for layer in t['board']:
#                    for row in layer:
#                        for column in row:
#                            if column == None:
#                                t['board'][layer][row][column] = 1
                               # statecopy.set((layer,row,column),1)
#                                iteration -= 1
#                                self.addChild(Tree(state, 0,iteration))

#        self.savetree()

#        try:
#            with open('tree.json', 'w') as file:
#                file.write(json.dumps(arbre))
#        except IOError:
#            print("Erreur d'entrée/sortie")







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