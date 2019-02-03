import datetime


class ProfileTimer:
    def __init__(self, name):
        self.name = name
        self.d = datetime.datetime.now()

    def mark(self, v):
        print(v, (datetime.datetime.now()-self.d).total_seconds())
