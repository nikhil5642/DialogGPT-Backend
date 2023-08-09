from threading import Thread
from time import sleep


def dailyChallengeService():
    while True:
        sleep(60*60*24)


# if __name__ == '__main__':
    # Thread(target=autoFollow).start()
    # sleep(60*60*1)