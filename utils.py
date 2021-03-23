from configparser import RawConfigParser as ConfigParser


def get_config(name):
    config_parser = ConfigParser()
    config_parser.read('config.ini')

    config = {}
    for section in ['global', name]:
        try:
            config.update(dict(config_parser[section]))
        except KeyError:
            pass

    return config
