import logging

logging.basicConfig(
    filename="LogGenerated.txt",
    format="%(asctime)s %(levelname)s %(filename)s Line:%(lineno)d %(message)s",
    datefmt="%m/%d/%Y %I:%M:%S %p",
    level=logging.ERROR,
)


def GlobalLogger():
    return logging
