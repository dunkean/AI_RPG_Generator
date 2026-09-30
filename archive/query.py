# import base64

from datetime import datetime
import hashlib
import os
import time
# import backoff

import defines as D


class LLM_Query():
    def __init__(self, LLM, Logger):
        self.LLM = LLM
        self.Logger = Logger
        self.cache_folder = os.path.join(D.CACHE_FOLDER, LLM.model_name)
        if not os.path.exists(self.cache_folder):
            os.makedirs(self.cache_folder)

    def set_cache(self, content, hash):
        filename = os.path.join(self.cache_folder, f"{hash}")
        with open(filename, "w") as outfile:
            outfile.write(content)

    def get_cache(self, hash):
        filename = os.path.join(self.cache_folder, f"{hash}")
        if os.path.exists(filename):
            with open(filename, "r") as infile:
                content = infile.read()
                print("Using cache: ", filename)
                return content
        return None

    def set_project_cache(self, content, project_hash):
        currentDateAndTime = datetime.now().strftime("%m-%d_%H-%M-%S_%f")[:-3]
        filename = os.path.join(self.cache_folder, f"{project_hash}_{currentDateAndTime}")
        with open(filename, "w") as outfile:
            outfile.write(content)

    def get_project_cache(self, project_hash):
        files = os.listdir(self.cache_folder)
        files.sort(key=lambda x: os.path.getmtime(os.path.join(self.cache_folder, x)))
        files = [f for f in files if f.startswith(project_hash)]
        if len(files) == 0:
            return None

        filename = os.path.join(self.cache_folder, files[-1])
        with open(filename, "r") as infile:
            content = infile.read()
            # print("Using cache: ", filename)
            return content

    def hash(self, prompt):
        hash_prompt = prompt.encode("utf-8")
        return hashlib.md5(hash_prompt).hexdigest()

    def get_cache_type(self, cache_type, prompt, parser, id="", type="", *, options=None):
        cache_content = None
        if cache_type == "hash":
            hash = self.hash(id + prompt)
            cache_content = self.get_cache(hash)
        elif cache_type == "project":
            project_hash = f"{id}_{type}"
            cache_content = self.get_project_cache(project_hash)
        
        if cache_content is None:
            return None
        else:
            return parser(cache_content)

    # @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    # force_cache: if True, will not query the cache based on the prompt but based on the last cached prompt for project/type (use with care cause it might introduce compatibility crashes)
    def query(self, prompt, parser, id="", type="", force_human_readable_cache=True, *, options=None):
        hash = self.hash(id + prompt)
        project_hash = f"{id}_{type}"
        if force_human_readable_cache:
            content = self.get_project_cache(project_hash)
        else:
            content = self.get_cache(hash)
        tries = 0
        response = None
        while content is None or parser(content) is None:
            if tries > 3:
                print("Failed to query: ", id, type)
                return None
            elif tries > 1:
                print("Retrying query: ", id, type)
                time.sleep(15)

            print("Querying OpenAI: ", id, type, hash, project_hash)
            content, response = self.LLM.query(prompt, options={"id": id, "type": type})
            # print("Response: ", response)
            tries += 1

        self.Logger.log(content, id=id, type=type)
        self.Logger.log(str(response), id=id, type=type + "_response")
        self.set_cache(content, hash)
        self.set_project_cache(content, project_hash)
        return parser(content)
