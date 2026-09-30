from threading import Thread, Lock
import time
import cache as C
import defines as D
# import LLM_query

patches = {}
threads = []
lock = Lock()
stop_queue = False


def update_dict(original, update):
    for key, value in update.items():
        # Add new key values
        if key not in original:
            original[key] = update[key]
            continue

        # Update the old key values with the new key values
        if key in original:
            if isinstance(value, dict):
                update_dict(original[key], update[key])
            if isinstance(value, list):
                update_list(original[key], update[key])
            if isinstance(value, (str, int, float)):
                original[key] = update[key]
    return original


def update_list(original, update):
    # Make sure the order is equal, otherwise it is hard to compare the items.
    assert len(original) == len(update), "Can only handle equal length lists."

    for idx, (val_original, val_update) in enumerate(zip(original, update)):
        if not isinstance(val_original, type(val_update)):
            raise ValueError(f"Different types! {type(val_original)}, {type(val_update)}")
        if isinstance(val_original, dict):
            original[idx] = update_dict(original[idx], update[idx])
        if isinstance(val_original, (tuple, list)):
            original[idx] = update_list(original[idx], update[idx])
        if isinstance(val_original, (str, int, float)):
            original[idx] = val_update
    return original


# def query(query_name, content, prompts, parser, validator, cache_options=("all", "all")) -> None:
#     if isinstance(prompts, tuple):
#         prompts = [prompts]

#     cache_type, cache_steps = cache_options
#     if "all" in cache_steps:
#         cache_steps = [D.QSTEP_PROMPT, D.QSTEP_PATCH, D.QSTEP_RESPONSE, D.QSTEP_NEW_CONTENT]
#     if "all" in cache_type:
#         cache_type = ["hash", "project_id"]

#     queue = []

#     def query_data(prompt_id, prompt):
#         global patches
#         patch = None
#         response = None
#         tries = 0

#         while patch is None:
#             if tries > 2:
#                 print("Failed to query: ", prompt_id)
#                 break

#             response = LLM_query(prompt_str)
#             if response is not None:
#                 C.setCache(prompt_id, D.QSTEP_RESPONSE, response)
#             patch = validator(parser(response))
#             if patch is not None:
#                 C.setCache(prompt_id, D.QSTEP_PATCH, patch)
#                 time.sleep(D.LLM_QUERY_DELAY)
#             tries += 1

#         with lock:
#             C.setCache(D.QSTEP_PATCH, patch)
#             patches[prompt_id] = patch

#     def queue_worker():
#         global stop_queue
#         global threads
#         while True:
#             for prompt_id, prompt in queue:
#                 thread = Thread(target=query_data, args=(prompt_id, prompt))
#                 threads.append(thread)
#                 thread.start()
#                 time.sleep(D.LLM_QUERY_DELAY)
#             time.sleep(0.5)
#             if stop_queue:
#                 break

#     queue_thread = Thread(name="queue", target=queue_worker())
#     queue_thread.start()

#     if C.hasCache(D.QSTEP_NEW_CONTENT, query_name, content, cache_type) and D.QSTEP_NEW_CONTENT in cache_steps:
#         content = C.getCache(D.QSTEP_NEW_CONTENT, query_name, content, cache_type)
#     else:
#         for tpl in prompts:
#             prompt_id, prompt_func = tpl[0], tpl[1]
#             ## get 3 values for prompt parameters
#             prompt_str = prompt_func(content) #add params as 
#             cache_params = (prompt_id, prompt_str, cache_type)

#             if C.hasCache(D.QSTEP_PATCH, *cache_params) and D.QSTEP_PATCH in cache_steps:
#                 with lock:
#                     patches[prompt_id] = C.getCache(D.QSTEP_PATCH, *cache_params)
#             else:
#                 if C.hasCache(D.QSTEP_RESPONSE, *cache_params) and D.QSTEP_RESPONSE in cache_steps:
#                     response = C.getCache(D.QSTEP_RESPONSE, *cache_params)
#                     with lock:
#                         patches[prompt_id] = validator(parser(response))
#                 else:
#                     if C.hasCache(D.QSTEP_PROMPT, *cache_params) and D.QSTEP_PROMPT in cache_steps:
#                         prompt_str = C.getCache(D.QSTEP_PROMPT, *cache_params)
#                     else:
#                         prompt_str = prompt_func(content)
#                         C.setCache(D.QSTEP_PROMPT, prompt_id, prompt_str)
#                     queue.append((prompt_id, prompt_str))

#     for thread in threads:
#         thread.join()

#     stop_queue = True
#     queue_thread.join()

#     for k, v in patches.items():
#         if v is None:
#             print("PATCH QUERY FAILED: ", k)
#         print("Patches: ", k)
#         # content.update(v)
#         update_dict(content, v)

#     C.setCache(query_name, D.QSTEP_NEW_CONTENT, content)
