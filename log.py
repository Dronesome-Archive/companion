import logging


def warn(*args):
    logging.getLogger().warning(' '.join([str(arg) for arg in args]))


def info(*args):
    logging.getLogger().info(' '.join([str(arg) for arg in args]))


def setup():
    logging.basicConfig(
        filename='log',
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)s\t[%(funcName)s] %(message)s',
        datefmt='%y-%m-%d %H:%M:%S'
    )
    logging.getLogger().addHandler(logging.StreamHandler())  # without this, errors only go to log, not stderr
