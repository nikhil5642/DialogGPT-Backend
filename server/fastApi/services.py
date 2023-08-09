from threading import Thread
from time import sleep

from server.fastApi.modules.dailyChallengeManagement import \
    sendDailyEmailAndTweetForAllSubscribers


from server.fastApi.modules.dailyMateInXChallengeManagement import \
    tweetMateInXPuzzle
from server.fastApi.modules.dailyQuotes import tweetNextQuote
from src.twitter.tweetGenerator import autoFollowChessComLikesUser, autoFollowChessComUsers, autoFollowChessLikingUser


def dailyChallengeService():
    while True:
        sendDailyEmailAndTweetForAllSubscribers()
        sleep(60*60*24)


def dailyMateInXPuzzle():
    while True:
        tweetMateInXPuzzle()
        sleep(60*60*24)


def dailyQuotes():
    while True:
        tweetNextQuote()
        sleep(60*60*24)


def autoFollow():
    sleep(60*5)
    while True:
        # autoFollowChessComUsers()
        autoFollowChessComLikesUser()
        # autoFollowChessLikingUser()
        sleep(60*60*8)

# Twitter API PROBLEM
#
# if __name__ == '__main__':
    # Thread(target=autoFollow).start()
    # sleep(60*60*1)
    # Thread(target=dailyMateInXPuzzle).start()
    # sleep(60*60*8)
    # Thread(target=dailyQuotes).start()
    # sleep(60*60*8)
    # Thread(target=dailyChallengeService).start()
