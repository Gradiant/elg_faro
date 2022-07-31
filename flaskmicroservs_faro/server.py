import os
import sys
import json
import yaml
import traceback
import logging
import subprocess
import threading
from flask import Flask, request
from flask_json import FlaskJSON, JsonError, as_json
from werkzeug.utils import secure_filename
from faro.faro_entrypoint import faro_execute as execute


logger = logging.getLogger(__name__)


#UPLOAD_FOLDER="/opt/faro/results"
UPLOAD_FOLDER="results/"

class Faro_Parameters(object):

    def __init__(self, input_file,
                 output_entity_file,
                 output_score_file,
                 split_lines,
                 verbose,
                 dump):
        self.input_file = input_file
        self.output_entity_file = output_entity_file
        self.output_score_file = output_score_file
        self.split_lines = split_lines
        self.verbose = verbose
        self.dump = dump
        

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
APP_ROOT = "./"
app.config["APPLICATION_ROOT"] = APP_ROOT
app.config["JSON_ADD_STATUS"] = False
app.config["JSON_SORT_KEYS"] = False
app.config["MAX_CONTENT_PATH"] = 20000000
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

json_app = FlaskJSON(app)


condition_lock = threading.Condition()


@app.route("/analyse", methods=["POST"])
def analyse():

    try:

        f = request.files['file']
        f.save(secure_filename(f.filename))

        logger.info("FILENAME: {}".format(f.filename))
        
        # execute FARO
        parameters = Faro_Parameters(
            input_file=f.filename,
            output_entity_file=f.filename + ".entity",
            output_score_file=f.filename + ".score",
            split_lines=False,
            verbose=False,
            dump=False
        )
            
        execute(parameters)

        logger.info("Reading data")
        
        # Read output
        with open(f.filename + ".entity", "r") as f_in:
            entity_object = json.load(f_in)

        with open(f.filename + ".score", "r") as f_in:
            score_object = json.load(f_in)
        
        result_object = {"score_file": score_object,
                         "entity_file": entity_object}
            
        # delete temporal files
        os.remove(f.filename + ".entity")
        os.remove(f.filename + ".score")
        os.remove(f.filename)

        return generate_successful_response(result_object)

    except Exception as e:

        if os.path.exists(f.filename):
            os.remove(f.filename)

        if os.path.exists(f.filename + ".entity"):
            os.remove(f.filename + ".entity")

        if os.path.exists(f.filename + ".score"):
            os.remove(f.filename + ".score")
        
        logger.error("Exception {}".format(traceback.format_exc()))
        
        return generate_failure_response(
            status=404,
            code="elg.service.internalError",
            text=None,
            params=None,
            detail=e,
        )

@json_app.invalid_json_error
def invalid_request_error(e):
    """Generates a valid ELG "failure" response if the request cannot be parsed"""
    raise JsonError(
        status_=400,
        failure={
            "errors": [
                {"code": "elg.request.invalid", "text": "Invalid request message"}
            ]
        },
    )


def generate_successful_response(result_object):
    """Generates the dict with the text classification reponse with the elg format
    :param result_object: dictionary with the result of the prediction
    :return: a dict with the response
    """
    response = {
        "type": "classification",
        "classes": [{"class": result_object["score_file"]["score"]}],
    }
    output = {"response": response}
    return output


def generate_failure_response(status, code, text, params, detail):
    """Generate a wrong response indicating the failure
    :param status: api error code
    :param code: ELG error type
    :param text: not used
    :param params: not used
    :param detail: detail of the exception
    """

    error = {}
    if code:
        error["code"] = code
    if text:
        error["text"] = text
    if params:
        error["params"] = params
    if detail:
        error["detail"] = str(detail)

    raise JsonError(status_=status, failure={"errors": [error]})


def run_flask_api(port):
    app.run(host="0.0.0.0", port=port)
