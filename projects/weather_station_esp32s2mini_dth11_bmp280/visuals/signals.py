from collections import deque

class Signal:
    __keyVal:str = 'val'
    __keyNanCnt:str = 'nanCnt'
    __keyGrdCnt:str = 'grdCnt'

    def __init__(self, maxLen:int = 100) -> None:
        self.val:deque[float] = deque(maxlen=maxLen)
        self.nanCnt:deque[int] = deque(maxlen=maxLen)
        self.grdCnt:deque[int] = deque(maxlen=maxLen)

    def updateVals(self, dctIn:dict):
        self.val.append(dctIn.get(self.__keyVal, 0.0))
        self.nanCnt.append(dctIn.get(self.__keyNanCnt, 0))
        self.grdCnt.append(dctIn.get(self.__keyGrdCnt, 0))

    def getKeys(self):
        return self.__keyVal, self.__keyNanCnt, self.__keyGrdCnt
