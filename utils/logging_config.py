import logging

def get_logger():
    logger=logging.getLogger('bo1')
    if not logger.handlers:
        handler=logging.StreamHandler(); handler.setFormatter(logging.Formatter('%(levelname)s %(message)s')); logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
