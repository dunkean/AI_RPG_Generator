from threading import Thread, Lock
import time
import cache as C
import defines as D
import LLM_query

patches = {}
threads = []
lock = Lock()
stop_queue = False


def query(content, prompts, parser, formatter, cache_options=("all", "all")):
    if isinstance(prompts, tuple):
        prompts = [prompts]

    cache_type, cache_steps = cache_options
    if "all" in cache_steps:
        cache_steps = ["prompt", "response", "parsed", "formatted", "patch", "content_updated"]
    if "all" in cache_type:
        cache_type = ["hash", "project_id"]

    queue = []

    def query_data(prompt_id, prompt):
        global patches
        patch = None
        response = None
        tries = 0

        while patch is None:
            if tries > 2:
                print("Failed to query: ", prompt_id)
                break

            response = LLM_query(prompt_str)
            if response is not None:
                C.setCache(prompt_id, "response", response)
            patch = formatter(parser(response))
            if patch is not None:
                C.setCache(prompt_id, "patch", patch)
                time.sleep(D.LLM_QUERY_DELAY)
            tries += 1

        with lock:
            C.setCache("patch", patch)
            patches[prompt_id] = patch

    def queue_worker():
        global stop_threads
        global threads
        while True:
            for prompt_id, prompt in queue:
                thread = Thread(target=query_data, args=(prompt_id, prompt))
                threads.append(thread)
                thread.start()
                time.sleep(D.LLM_QUERY_DELAY)
            time.sleep(0.5)
            if stop_queue:
                break

    queue_thread = Thread(name="queue", target=lambda: queue_worker())
    queue_thread.start()

    for prompt_id, prompt_func in prompts:
        prompt_str = prompt_func(content)
        cache_params = (prompt_id, prompt_str, cache_type)

        if C.hasCache("content_updated", *cache_params) and "content_updated" in cache_steps:
            content = C.getCache("content_updated", *cache_params)
        else:
            if C.hasCache("patch", *cache_params) and "patch" in cache_steps:
                with lock:
                    patches[prompt_id] = C.getCache("patch", *cache_params)
            else:
                if C.hasCache("response", *cache_params) and "response" in cache_steps:
                    response = C.getCache("response", *cache_params)
                    with lock:
                        patches[prompt_id] = formatter(parser(response))
                else:
                    if C.hasCache("prompt", *cache_params) and "prompt" in cache_steps:
                        prompt_str = C.getCache("prompt", *cache_params)
                    else:
                        prompt_str = prompt_func(content)
                        C.setCache("prompt", prompt_id, prompt_str)
                    queue.append((prompt_id, prompt_str))

    for thread in threads:
        thread.join()

    stop_queue = True
    queue_thread.join()

    for k, v in patches.items():
        if v is None:
            print("PATCH QUERY FAILED: ", k)
        print("Patches: ", k)
        content.update(v)

    C.setCache(prompt_id, "content_updated", content)

# def query(self, prompt, parser, id="", type="", force_human_readable_cache=True, *, options=None):
#         hash = self.hash(id + prompt)
#         project_hash = f"{id}_{type}"
#         if force_human_readable_cache:
#             content = self.get_project_cache(project_hash)
#         else:
#             content = self.get_cache(hash)
#         tries = 0
#         response = None
#         while content is None or parser(content) is None:
#             if tries > 3:
#                 print("Failed to query: ", id, type)
#                 return None
#             elif tries > 1:
#                 print("Retrying query: ", id, type)
#                 time.sleep(15)

#             print("Querying OpenAI: ", id, type, hash, project_hash)
#             content, response = self.LLM.query(prompt, options={"id": id, "type": type})
#             # print("Response: ", response)
#             tries += 1

#         self.Logger.log(content, id=id, type=type)
#         self.Logger.log(str(response), id=id, type=type + "_response")
#         self.set_cache(content, hash)
#         self.set_project_cache(content, project_hash)
#         return parser(content)



    