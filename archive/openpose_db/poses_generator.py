import webuiapi
import os
import json
import random
from PIL import Image
import base64
import requests
api = webuiapi.WebUIApi(host='127.0.0.1', port=7860)


def submit_post(url: str, data: dict):
    """
    Submit a POST request to the given URL with the given data.
    """
    return requests.post(url, data=json.dumps(data))


def save_encoded_image(b64_image: str, output_path: str):
    """
    Save the given image to the given output path.
    """
    with open(output_path, "wb") as image_file:
        image_file.write(base64.b64decode(b64_image))


def encode_image(image_path):
    with open(image_path, "rb") as i:
        b64 = base64.b64encode(i.read())
    return b64.decode("utf-8")


api.util_set_model('dreamlikeDiffusion10_10.ckpt [0aecbcfa2c]')


# fine art painting full body, working pose, view of a female elf adult, casual outfit, white background
negative = """text, watermark, (two people), (multiple people), (two faces), bad art, (((hat))), ((cut head)), (head out of frame), (playing card), card, (((out of frame)))((extra limbs)), cloned face, gross proportions, (malformed limbs), ((missing arms)), ((missing legs)), (((extra arms))), (((extra legs)))"""
# Steps: 15, Sampler: DPM++ 2S a Karras, CFG scale: 7, Seed: 390763734, Size: 512x768, Model hash: 0aecbcfa2c, Model: dreamlikeDiffusion10_10


heights = ["small",
           "normal height",
           "tall"]

weights = ["skinny",
           "normal weight",
           "muscular",
           "fat"]

races = ["caucasian",
         "elf",
         "dwarf",
         "gnome"]
ages = [ 
        (0, 5, "Infant", "infant"),
        (5, 10, "Boy", "boy"),
        (10, 15, "pre-teen", "preteen"),
        (15, 20, "Teenager", "teenager"),
        (20, 25, "Young adult", "young adult"),
        (25, 40, "Adult in his thirties", "thirties"),
        (40, 60, "Middle-aged", "middle aged"),
        (60, 85, "Elderly", "elderly"),
        (85, 130, "Very old, bent man", "very old")]
genders = ["male", "female"]

n_iterations = 1
combinations = len(heights) * len(weights) * len(races) * len(ages) * len(genders) * n_iterations
print(f"Generating {combinations} images...")
generated = 0
for gender in genders:
    for height in heights:
        for weight in weights:
            for race in races:
                for age in ages:
                    age_str = age[2]
                    if age_str == "Boy" and gender == "female":
                        age_str = "Girl"
                    
                    race_prefix = "human" if race == "caucasian" else race
                    weight_prefix = weight.replace(" weight", "")
                    height_prefix = height.replace(" height", "")
                    img_prefix = f"""{race_prefix}_{gender}_{age[3]}_{weight_prefix}_{height_prefix}"""
                    
                    idx = 0
                    while os.path.exists(f"""./{img_prefix}_{str(idx)}.jpg"""):
                        idx += 1
                    if race_prefix != "human" and idx >= 5:
                        break
                    elif race_prefix == "human" and idx >= 12:
                        break
                    print(f"""{img_prefix}_{str(idx)}""")
                    
                    
                    prompt = f"""fine art painting, heroic fantasy, full body, frontal view of a ((single)) {race} {gender}, {height}, (({age[2]})) and {weight}, simple dark outfit, casual pose, white gradient background, realistic"""

                    data = {
                            "prompt": prompt,
                            "negative_prompt": negative,
                            # "init_images": [image],	# For img2img
                            "sampler_name": 'DPM++ 2S a Karras',
                            "seed": -1,
                            "cfg_scale": 6,
                            "n_iter": n_iterations,
                            "steps": 15,
                            "batch_size": 5,
                            "width": 512,
                            "height": 768,
                            }
                    query_url = 'http://127.0.0.1:7860/sdapi/v1/txt2img'
                    response = submit_post(query_url, data)

                    for img in response.json()['images']:
                        idx = 0
                        while os.path.exists(f"""./{img_prefix}_{str(idx)}.jpg"""):
                            idx += 1
                        generated += 1
                        img_path = f"""./{img_prefix}_{str(idx)}.jpg"""
                        save_encoded_image(img, img_path)

            print(f"Generated {generated} images out of {combinations}...")






# data = {
#         "prompt": prompt,
#         "negative_prompt": negative,
#         # "init_images": [image],	# For img2img
#         "sampler_name": 'DPM++ 2S a Karras',
#         "seed": -1,
#         "cfg_scale": 7,
#         "n_iter": 1,
#         "steps": 15,
#         "batch_size": 1,
#         "width": 512,
#         "height": 768,
#         # "restore_faces": True,
#         # "enable_hr": True,
#         # "denoising_strength": 0.6,
#         # "hr_scale": 2,
#         # "hr_upscaler": "Latent",
#         # "hr_resize_x": width*2,
#         # "hr_resize_y": height*2,
#         # "alwayson_scripts": {
#         #     "controlnet": {
#         #         "args": [
#         #             {
#         #                 "input_image": pose_img,
#         #                 # "module": "depth","model": "control_depth-fp16 [400750f6]"
#         #                 "module": "none" if pose_on else "openpose", "model": "control_openpose-fp16 [9ca67cc5]",
#         #             }
#         #         ]
#         #     }
#         # }
#         }