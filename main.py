from server.fastApi.modules.dailyQuotes import tweetNextQuote
from src.twitter.threadsGenerator import createThreadsPost
from src.twitter.tweetGenerator import autoFollowChessComLikesUser, autoFollowChessComUsers, unfollowAll
from src.twitter.urlShortner import getShortenUrl

if __name__ == '__main__':
    # updateAllTickerCharts()
    # buyOneBucketFromExchange("bucket_x")
    # sellOneBucketFromExchange("bucket_x")
    # item = {ID: "BTC", AMOUNT_PER_UNIT: 0.0000}
    # print(getTickerContribution(item, 2))
    # autoFollowChessComUsers()
    # unfollowAll()
    # autoFollowChessComLikesUser()
    createThreadsPost("Account Setup Done")
    print("sdfasl;jk")
