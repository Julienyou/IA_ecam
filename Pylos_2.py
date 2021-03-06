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
                        [None] * size)  # None signifie qu'il n'y a rien donc sur le plateau on met tout à none au debut
                return matrix

            board = []
            for i in range(4):
                board.append(squareMatrix(4 - i))

            initialstate = {  # initialise le jeu
                'board': board,
                'reserve': [15, 15],
                'turn': 0
            }

        super().__init__(initialstate)

    def get(self, layer, row, column):  # regarde si on sait mettre une bille sur le plateau si elle correspond au dimension etc ...
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
        if self.get(layer, row, column) != None:  # il regarde dans la liste si la valeur est different de none ce qui signifierait qu'il y a deja une bille sur la position
            raise game.InvalidMoveException('The position ({}) is not free'.format([layer, row, column]))

        if layer > 0:  # si il y a une bille qui manque donc qu'on essaie de monter une bille sur 3 billes il dit que c'est pas stable et provoque une erreur
            if (
                                    self.get(layer - 1, row, column) == None or
                                    self.get(layer - 1, row + 1, column) == None or
                                self.get(layer - 1, row + 1, column + 1) == None or
                            self.get(layer - 1, row, column + 1) == None
            ):
                raise game.InvalidMoveException('The position ({}) is not stable'.format([layer, row, column]))

    def canMove(self, layer, row, column):  # regarde si la bille peut bouger
        if self.get(layer, row, column) == None:  # impossible car none donc il y a pas de bille
            raise game.InvalidMoveException('The position ({}) is empty'.format([layer, row, column]))

        if layer < 3:  # regarde si il y a quelque chose au dessus
            if (
                                    self.safeGet(layer + 1, row, column) != None or
                                    self.safeGet(layer + 1, row - 1, column) != None or
                                self.safeGet(layer + 1, row - 1, column - 1) != None or
                            self.safeGet(layer + 1, row, column - 1) != None
            ):
                raise game.InvalidMoveException('The position ({}) is not movable'.format([layer, row, column]))

    def createSquare(self, coord):
        layer, row, column = tuple(coord)

        def isSquare(layer, row, column):  # regarde si il y a un carre autour d'une bille
            if (
                self.safeGet(layer, row, column) != None and
                self.safeGet(layer, row + 1, column) == self.safeGet(layer, row, column) and
                self.safeGet(layer, row + 1, column + 1) == self.safeGet(layer, row, column) and
                self.safeGet(layer, row, column + 1) == self.safeGet(layer, row, column)
            ):
                return True
            return False

        if (  # regarde les differents elements qui sont juste a cote pour voir si il y a un carre
                    isSquare(layer, row, column) or
                    isSquare(layer, row - 1, column) or
                    isSquare(layer, row - 1, column - 1) or
                    isSquare(layer, row, column - 1)
        ):
            return True
        return False

    def set(self, coord, value):  # met la bille
        layer, row, column = tuple(coord)
        self.validPosition(layer, row, column)
        self._state['visible']['board'][layer][row][column] = value

    def remove(self, coord, player):  # enleve la bille
        layer, row, column = tuple(coord)
        self.canMove(layer, row, column)
        sphere = self.get(layer, row, column)
        if sphere != player:
            raise game.InvalidMoveException('not your sphere')
        self._state['visible']['board'][layer][row][column] = None

    # update the state with the move
    # raise game.InvalidMoveException
    def update(self, move, player):  # fais un etat du jeu, enleve la bille dans la reserve,et fais jouer l'autre joueur
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
        if state['reserve'][0] < 1:  # si le player 0 n'a plus de boules -> 1 gagne
            return 1
        elif state['reserve'][1] < 1:  # si l'autre n'a plus de boules -> 0 gagne
            return 0
        return -1

    def val2str(self, val):  # affichage
        return '_' if val == None else '@' if val == 0 else 'O'

    def player2str(self, val):
        return 'Light' if val == 0 else 'Dark'

    def printSquare(self, matrix):
        print(' ' + '_' * (len(matrix) * 2 - 1))
        print('\n'.join(map(lambda row: '|' + '|'.join(map(self.val2str, row)) + '|', matrix)))

    # print the state
    def prettyprint(self):
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
                                    removableballs.apppend([layer,row,column])
                                else:
                                    removableballs = self.removableballs1(test_pylos)
                                    removableballs.apppend([layer, row, column])
                                for i in removableballs:
                                    if i[0] == layer - 1 and i[1] == row and i[2] == column:  # self.get(layer - 1, row, column) == None or
                                        removableballs.remove(i)
                                    elif i[0] == layer - 1 and i[1] == row + 1 and i[2] == column:  # self.get(layer - 1, row + 1, column) == None or
                                        removableballs.remove(i)
                                    elif i[0] == layer - 1 and i[1] == row + 1 and i[2] == column + 1:  # self.get(layer - 1, row + 1, column + 1) == None or
                                        removableballs.remove(i)
                                    elif i[0] == layer - 1 and i[1] == row and i[2] == column + 1:  # self.get(layer - 1, row, column + 1) == None
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

    def holes(self, test_pylos):                                        #dans la liste availableHoles, on met les listes [LAYER, ROW, column] qui seront les coord de chaque trou possible
        availableholes = []
        for layer in range(1, 4):                                           #il ne faudra de toute façon pas prendre les trous de la première layer en compte
            for row in range(4 - layer):
                for column in range(4 - layer):
                    value = test_pylos.get(layer, row, column)
                    if value is None:                                       #c'est un trou (car value == None)
                        try:
                            test_pylos.validPosition(layer, row, column)    #est ce que c'est un trou valide ? (pas de boule dessus?)
                            hole = [layer, row, column]                     #alors on met layer, row et column dans une liste hole
                        except game.InvalidMoveException:                   #si pas un trou valide ; on passe à la case suivante
                            pass
                        else:
                            availableholes.append(hole)                         #on ajoute la liste hole à la liste availableHoles
        return availableholes                                               #retourne la liste qui contient toutes les listes des emplacements des trous valides

    def removableballs0(self, test_pylos):
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
        possibilities = []  # liste qui contiendra move (dictionnaire avec la sorte de move, de où à où)
        if test_pylos._state['visible']['turn'] is 0:  # si c'est le tour du joueur 0 : on cherche les 0
            for layer in range(4):
                for row in range(4 - layer):
                    for column in range(4 - layer):
                        value = test_pylos.get(layer, row, column)
                        if value is 0:  # on cherche les 0 (toutes nos balles)
                            try:
                                test_pylos.canMove(layer, row,column)  # peut-on la bouger ? est ce qu'il n'y a pas de boule dessus?
                            except game.InvalidMoveException:  # si la réponse est non, on passe à la case suivante
                                pass
                            availableholes = self.holes(test_pylos)  # on va rechercher la variable availableHoles qui contient tous les trous valides du jeu (y compris les non-vaides dê à la boule qu'on va prendre)
                            for i in availableholes:  # on va voir dans chaque trou (exprimé en une liste [layer, row, column]
                                if i[0] <= layer:  # checke si les layers des trous sont pas en dessous ou au même niveau que layer
                                    availableholes.remove(i)
                                elif i[0] == layer + 1 and i[1] == row and i[2] == column:  # pour ce cas-ci : self.get(layer + 1, row, column) == None or
                                    availableholes.remove(i)
                                elif i[0] == layer + 1 and i[1] == row + 1 and i[0] == column:  # pour ce cas-ci : self.get(layer + 1, row + 1, column) == None or
                                    availableholes.remove(i)
                                elif i[0] == layer + 1 and i[1] == row + 1 and i[0] == column + 1:  # pour ce cas-ci : self.get(layer + 1, row + 1, column + 1) == None or
                                    availableholes.remove(i)
                                elif i[0] == layer + 1 and i[1] == row and i[0] == column + 1:  # pour ce cas-ci : self.get(layer + 1, row, column + 1) == None
                                    availableholes.remove(i)

                            # maintenant il nous reste une liste avec juste les bons trous qui sont valides.
                            # pour tous les trous dans cette liste, on peut les mettre dans le 'to' :

                            for i in availableholes:
                                move = {
                                    'move': 'move',
                                    'from': [layer, row, column],
                                    'to': i
                                }
                                possibilities.append(move)

                            if test_pylos.createSquare((layer, row, column)) is True:  # si ca forme un carré
                                # on va recevoir removableballs1 et on va enlever les boules qui sont en dessous de la boule qu'on vient de placer et enlever la boule qu'on vient de bouger ET on va rajouter celle qu'on vient de placer (son nouvel emplacement)
                                removableballs0 = self.removableballs0(test_pylos)
                                for i in removableballs0:
                                    if i[0] == layer - 1 and i[1] == row and i[2] == column:  # self.get(layer - 1, row, column) == None or
                                        removableballs0.remove(i)
                                    elif i[0] == layer - 1 and i[1] == row + 1 and i[2] == column:  # self.get(layer - 1, row + 1, column) == None or
                                        removableballs0.remove(i)
                                    elif i[0] == layer - 1 and i[1] == row + 1 and i[2] == column + 1:  # self.get(layer - 1, row + 1, column + 1) == None or
                                        removableballs0.remove(i)
                                    elif i[0] == layer - 1 and i[1] == row and i[2] == column + 1:  # self.get(layer - 1, row, column + 1) == None
                                        removableballs0.remove(i)
                                    elif i[0] == layer and i[1] == row and i[2] == column:  # la boule qu'on a montée n'est plus valable en tant que removableballs
                                        removableballs0.remove(i)
                                    removableballs0.append(i)  # on ajoute la boule qu'on vient de placer dans les removableballs
                                removableballs01 = copy.deepcopy(removableballs0)  # mtnt on a deux listes avec les removableballs
                                for i in removableballs0:
                                    for j in removableballs01:
                                        if i != j:
                                            removewhat = []
                                            removewhat.append([i, j])
                                            move['remove'] = removewhat
                                        else:
                                            pass
                                possibilities.append(move)


        else:                  # si c'est le tour du joueur 1, il faut chercher les 0 (d'après ce que j'ai vu quand j'ai lancé le jeu (pas logique)
            for layer in range(4):
                for row in range(4 - layer):
                    for column in range(4 - layer):
                        value = test_pylos.get(layer, row, column)
                        if value is 1:  # on cherche les 1 (toutes nos balles)
                            try:
                                test_pylos.canMove(layer, row, column)              #partie pour 'from'
                            except game.InvalidMoveException:
                                pass

                            availableholes = self.holes(test_pylos)                 #partie pour 'to'

                            for i in availableholes:  # check si les layers des trous sont pas en dessous ou au même niveau que layer
                                if i[0] <= layer:
                                    availableholes.remove(i)
                                elif i[0] == layer + 1 and i[1] == row and i[2] == column:  # pour ce cas-ci : self.get(layer + 1, row, column) == None or
                                    availableholes.remove(i)
                                elif i[0] == layer + 1 and i[1] == row + 1 and i[0] == column:  # pour ce cas-ci : self.get(layer + 1, row + 1, column) == None or
                                    availableholes.remove(i)
                                elif i[0] == layer + 1 and i[1] == row + 1 and i[0] == column + 1:  # pour ce cas-ci : self.get(layer + 1, row + 1, column + 1) == None or
                                    availableholes.remove(i)
                                elif i[0] == layer + 1 and i[1] == row and i[0] == column + 1:  # pour ce cas-ci : self.get(layer + 1, row, column + 1) == None
                                    availableholes.remove(i)

                            # maintenant il nous reste une liste avec juste les bons trous qui sont valides.
                            # pour tous les trous dans cette liste, on peut les mettre dans le 'to' :

                            for i in availableholes:
                                move = {
                                    'move': 'move',
                                    'from': [layer, row, column],
                                    'to': i
                                }
                            if test_pylos.createSquare((layer, row, column)) is True:  # si ca forme un carré
                                # on va recevoir removableballs1 et on va enlever les boules qui sont en dessous de la boule qu'on vient de placer et enlever la boule qu'on vient de bouger ET on va rajouter celle qu'on vient de placer (son nouvel emplacement)
                                removableballs1 = self.removableballs1()
                                for i in removableballs1:
                                    if i[0] == layer - 1 and i[1] == row and i[2] == column:  # self.get(layer - 1, row, column) == None or
                                        removableballs1.remove(i)
                                    elif i[0] == layer - 1 and i[1] == row + 1 and i[2] == column:  # self.get(layer - 1, row + 1, column) == None or
                                        removableballs1.remove(i)
                                    elif i[0] == layer - 1 and i[1] == row + 1 and i[2] == column + 1:  # self.get(layer - 1, row + 1, column + 1) == None or
                                        removableballs1.remove(i)
                                    elif i[0] == layer - 1 and i[1] == row and i[2] == column + 1:  # self.get(layer - 1, row, column + 1) == None
                                        removableballs1.remove(i)
                                    elif i[0] == layer and i[1] == row and i[2] == column:  # la boule qu'on a montée n'est plus valable en tant que removableballs
                                        removableballs1.remove(i)
                                    removableballs1.append(i)  # on ajoute la boule qu'on vient de placer dans les removableballs
                                removableballs11 = copy.deepcopy(removableballs1)  # mtnt on a deux listes avec les removableballs
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
        res0 = st._state['visible']['reserve'][0]
        res1 = st._state['visible']['reserve'][1]
        numero = st._state['visible']['numero']
        if st._state['visible']['turn'] is 0:
            delta = res0-res1
        else:
            delta = res1-res0
        return numero, delta

    def firstmoves_func(self, mouvements):
        self.firstmoves = []
        self.firstmoves.append(mouvements)
        return self.firstmoves                           #liste avec les mouvements

    def tree(self, st, iter):
        player = st._state['visible']['turn']
        numero = st._state['visible']['numero']
        #state = Pylos_copy._state['visible']
        placements = self.allplacement(st)          #liste avec les dicos "move" pour place
        upmoves = self.moveup(st)                   #liste avec les dicos "move" pour moveup
        mouvements = placements + upmoves           #liste avec TOUS les "move"
        if iter is 3:
            self.firstmoves_func(mouvements)      #renvoie la liste avec les mouvements de la première itération (pour pouvoir les utiliser après pour choisir le nextmove)
        children = []                               #liste vide
        if iter < 1:                                #????
            return Tree(st._state['visible'])
        self.deltas = []
        if iter == 3:
            iter -= 1
            for mouvement in mouvements:                #on prend chaque "move" de la liste
                Pylos_copy = copy.deepcopy(st)
                numero += 1
                Pylos_copy.update(mouvement, player)
                Pylos_copy._state['visible']['numero'] = numero
                self.deltas.append(self.delta_func(Pylos_copy))
    #            max_indice = [numero for numero, delta in self.deltas if delta == max(self.deltas[1])]
    #            Pylos_copy.set(mouvement['to'],player)
                child = self.tree(Pylos_copy, iter)
                children.append(child)
        else:
            iter -= 1
            for mouvement in mouvements:  # on prend chaque "move" de la liste
                Pylos_copy = copy.deepcopy(st)
                Pylos_copy.update(mouvement, player)
                Pylos_copy._state['visible']['numero'] = numero
                self.deltas.append(self.delta_func(Pylos_copy))
     #           max_indice = [numero for numero, delta in self.deltas if delta == max(self.deltas[1])]
                #            Pylos_copy.set(mouvement['to'],player)
                child = self.tree(Pylos_copy, iter)
                children.append(child)
        return Tree(st._state['visible'], children,)

    def mostfrequent(self,L):
        """Retourne l'élément le plus fréquent de la liste"""
        L.sort()  # pour que les éléments identiques soient assemblés
        n0, e0 = 0, None  # pour conserver le plus fréquent
        ep = None  # stocke l'élément distinct de la boucle précédente
        for e in L:
            if e != ep:  # si l'élément e n'a pas déjà été rencontré, on compte la frequence
                n = L.count(e)
                if n > n0:
                    n0, e0 = n, e  # on stocke le nouvel élément le plus fréquent
                ep = e  # on stocke l'élément courant pour la boucle suivante
        return e0, n0


    # return move as string
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

#        if state._state['visible']['reserve'][0] == 15:
#            pylosCopy = PylosState()
#            pylosCopy._state['visible']['numero'] = -1
#            print(self.tree(pylosCopy, 3))
#            print(self.firstmoves[0][0])
        print('coucou')
        if state._state['visible']['turn'] == 1:
            print('if ok')
            pylosCopy = copy.deepcopy(state)
            pylosCopy._state['visible']['numero'] = -1
            print(self.tree(pylosCopy, 3))
            for i in range(len(self.deltas)):
                print('for ok')
                max_indice = [numero for numero, delta in self.deltas if delta == max(self.deltas[i])]
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