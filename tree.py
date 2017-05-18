import copy


class Tree:
    def __init__(self, value, children=[]):
        self.__value = value
        self.__children = copy.deepcopy(children)

    def __getitem__(self, index):
        return self.__children[index]

    def __str__(self):
        def _str(tree, level):
            result = '[{}]\n'.format(tree.__value)
            for child in tree.children:
                result += '{}|--{}'.format('    ' * level, _str(child, level + 1))
            return result

        return _str(self, 0)

    @property
    def value(self):
        return self.__value

    @property
    def children(self):
        return copy.deepcopy(self.__children)

    @property
    def size(self):
        result = 1
        for child in self.__children:
            result += child.size
        return result

    def addChild(self, tree):
        self.__children.append(tree)


#c1 = Tree(25, [Tree(-9)])
#c2 = Tree(12)
#c3 = Tree(14)

#t = Tree(11, [c1, c2, c3])
#t[0][0].addChild(Tree(8))


# def treeMaker(n):
#    return Tree(1, [treeMaker(n-1) for i in range(n)])

# oxoTree = treeMaker(3)
# print(oxoTree)