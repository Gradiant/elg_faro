import logging
import yaml
from .server import run_flask_api


logger = logging.getLogger(__name__)


def execute(flask_port):
    """ Configuration of the flask API server 

    FLASK_PORT -- port of the flask API

    """

    run_flask_api(flask_port)
