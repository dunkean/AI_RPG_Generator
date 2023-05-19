import json
import os

from datetime import datetime

import defines as D


class Logger():
    def __init__(self):
        if not os.path.exists(D.LOG_FOLDER):
            os.path.makedirs(D.LOG_FOLDER)

    def log(self, content, *, id=None, type=None, suffix="txt"):
        currentDateAndTime = datetime.now().strftime("%m-%d_%H-%M-%S_%f")[:-2]

        filename = os.path.join(D.LOG_FOLDER, f"{currentDateAndTime}_{id}_{type}.{suffix}")
        if id is None or type is None:
            filename = os.path.join(D.LOG_FOLDER, f"{currentDateAndTime}.{suffix}")

        with open(filename, "w") as outfile:
            outfile.write(content)

    def log_json(self, content, *, id, type):
        self.log(json.dumps(content, indent=4), id=id, type=type, suffix="json")
