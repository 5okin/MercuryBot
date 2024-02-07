from PIL import Image
import json
from datetime import datetime
import urllib.request
from pathlib import Path


def create_combined_image(images):
    """
    Combines given list of images and returns new_image

    :param images: A list of images
    """
    if len(images) == 1:
        new_image = Image.new('RGB', (images[0].size[0], images[0].size[1]), (47,49,54,0))
        new_image.paste(images[0], (0, 0))
    elif len(images) == 2:
        new_image = Image.new('RGB', (images[0].size[0] + images[1].size[0], images[0].size[1]), (47, 49, 54, 0))
        new_image.paste(images[0], (0, 0))
        new_image.paste(images[1], (images[1].size[0], 0))
        new_image.thumbnail((new_image.size[0]//2, new_image.size[1]//2), Image.ANTIALIAS)
    elif len(images) == 3:
        new_image = Image.new('RGB', (images[0].size[0] + images[1].size[0], images[0].size[1]), (47, 49, 54, 0))
        new_image.paste(images[0], (0, 0))
        new_image.paste(images[1], (images[0].size[0], 0))
        new_image.paste(images[2], ((images[0].size[0] + images[1].size[0])//2, images[1].size[1]))
        new_image.thumbnail((new_image.size[0]//2, new_image.size[1]//2), Image.ANTIALIAS)
    return new_image


def merge_epic():

    curr_images = []
    next_images = []

    with open('./data/epic_database.json') as json_file:
        data = json.load(json_file)
        for game in data:
            date = datetime.strptime(game['startDate'], '%y-%m-%d %H:%M:%S')
            if date <= datetime.now():
                curr_images.append(Image.open(urllib.request.urlopen(game['image'])))
            else:
                next_images.append(Image.open(urllib.request.urlopen(game['image'])))

    new_curr_image = create_combined_image(curr_images)
    new_next_image = create_combined_image(next_images)

    if len(next_images) == 1:
        new_merged_image = Image.new('RGB', (new_curr_image.size[0] + new_next_image.size[0], new_next_image.size[1]), (47, 49, 54, 0))
        new_merged_image.paste(new_curr_image, (0, (new_next_image.size[1]//2 - new_curr_image.size[1]//2)))
        new_merged_image.paste(new_next_image, (new_curr_image.size[0], 0))
    else:
        new_merged_image = Image.new('RGB', (new_curr_image.size[0] + new_next_image.size[0], new_curr_image.size[1]), (47, 49, 54, 0))
        new_merged_image.paste(new_curr_image, (0, 0))
        new_merged_image.paste(new_next_image, (new_curr_image.size[0], (new_curr_image.size[1]//2 - new_next_image.size[1]//2)))

    new_merged_image.thumbnail((new_merged_image.size[0]//4, new_merged_image.size[1]//4), Image.ANTIALIAS)
    Path("./images").mkdir(parents=True, exist_ok=True)
    new_merged_image.save("./images/epic_image.jpg", "JPEG")


def merge_gog():
    images = []
    new_img_size = 0

    with open('./data/gog_database.json') as json_file:
        data = json.load(json_file)
        for game in data:
            images.append(Image.open(urllib.request.urlopen(game['image'])))

    for image in images:
        new_img_size += image.size[0]

    new_image = Image.new('RGB', (new_img_size, images[0].size[1]), (47, 49, 54, 0))

    size = 0 
    for image in images:
        new_image.paste(image, (size, 0))
        size += image.size[0]

    Path("./images").mkdir(parents=True, exist_ok=True)
    new_image.thumbnail((new_image.size[0]//4, new_image.size[1]//4), Image.ANTIALIAS)
    new_image.save("./images/gog_image.jpg", "JPEG")
