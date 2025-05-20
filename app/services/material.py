import os
import random
from typing import List, Literal
from urllib.parse import urlencode

import requests
from loguru import logger
from moviepy.video.io.VideoFileClip import VideoFileClip
from PIL import Image
import io

from app.config import config
from app.models.schema import MaterialInfo, VideoAspect, VideoConcatMode, MaterialType
from app.utils import utils

requested_count = 0


def get_api_key(cfg_key: str):
    api_keys = config.app.get(cfg_key)
    if not api_keys:
        raise ValueError(
            f"\n\n##### {cfg_key} is not set #####\n\nPlease set it in the config.toml file: {config.config_file}\n\n"
            f"{utils.to_json(config.app)}"
        )

    # if only one key is provided, return it
    if isinstance(api_keys, str):
        return api_keys

    global requested_count
    requested_count += 1
    return api_keys[requested_count % len(api_keys)]


def search_videos_pexels(
    search_term: str,
    minimum_duration: int,
    video_aspect: VideoAspect = VideoAspect.portrait,
) -> List[MaterialInfo]:
    aspect = VideoAspect(video_aspect)
    video_orientation = aspect.name
    video_width, video_height = aspect.to_resolution()
    api_key = get_api_key("pexels_api_keys")
    headers = {
        "Authorization": api_key,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    }
    # Build URL
    params = {"query": search_term, "per_page": 20, "orientation": video_orientation}
    query_url = f"https://api.pexels.com/videos/search?{urlencode(params)}"
    logger.info(f"searching videos: {query_url}, with proxies: {config.proxy}")

    try:
        r = requests.get(
            query_url,
            headers=headers,
            proxies=config.proxy,
            verify=False,
            timeout=(30, 60),
        )
        response = r.json()
        video_items = []
        if "videos" not in response:
            logger.error(f"search videos failed: {response}")
            return video_items
        videos = response["videos"]
        # loop through each video in the result
        for v in videos:
            duration = v["duration"]
            # check if video has desired minimum duration
            if duration < minimum_duration:
                continue
            video_files = v["video_files"]
            # loop through each url to determine the best quality
            for video in video_files:
                w = int(video["width"])
                h = int(video["height"])
                if w == video_width and h == video_height:
                    item = MaterialInfo()
                    item.provider = "pexels"
                    item.url = video["link"]
                    item.duration = duration
                    item.type = MaterialType.video
                    video_items.append(item)
                    break
        return video_items
    except Exception as e:
        logger.error(f"search videos failed: {str(e)}")

    return []


def search_videos_pixabay(
    search_term: str,
    minimum_duration: int,
    video_aspect: VideoAspect = VideoAspect.portrait,
) -> List[MaterialInfo]:
    aspect = VideoAspect(video_aspect)

    video_width, video_height = aspect.to_resolution()

    api_key = get_api_key("pixabay_api_keys")
    # Build URL
    params = {
        "q": search_term,
        "video_type": "all",  # Accepted values: "all", "film", "animation"
        "per_page": 50,
        "key": api_key,
    }
    query_url = f"https://pixabay.com/api/videos/?{urlencode(params)}"
    logger.info(f"searching videos: {query_url}, with proxies: {config.proxy}")

    try:
        r = requests.get(
            query_url, proxies=config.proxy, verify=False, timeout=(30, 60)
        )
        response = r.json()
        video_items = []
        if "hits" not in response:
            logger.error(f"search videos failed: {response}")
            return video_items
        videos = response["hits"]
        # loop through each video in the result
        for v in videos:
            duration = v["duration"]
            # check if video has desired minimum duration
            if duration < minimum_duration:
                continue
            video_files = v["videos"]
            # loop through each url to determine the best quality
            for video_type in video_files:
                video = video_files[video_type]
                w = int(video["width"])
                # h = int(video["height"])
                if w >= video_width:
                    item = MaterialInfo()
                    item.provider = "pixabay"
                    item.url = video["url"]
                    item.duration = duration
                    item.type = MaterialType.video
                    video_items.append(item)
                    break
        return video_items
    except Exception as e:
        logger.error(f"search videos failed: {str(e)}")

    return []


def search_images_pexels(
    search_term: str,
    image_aspect: VideoAspect = VideoAspect.portrait,
    image_type: Literal["all", "photo", "animation"] = "all",
    per_page: int = 40,
) -> List[MaterialInfo]:
    aspect = VideoAspect(image_aspect)
    image_orientation = aspect.name
    api_key = get_api_key("pexels_api_keys")
    headers = {
        "Authorization": api_key,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    }
    
    # Build URL
    params = {"query": search_term, "per_page": per_page, "orientation": image_orientation}
    query_url = f"https://api.pexels.com/v1/search?{urlencode(params)}"
    logger.info(f"searching images: {query_url}, with proxies: {config.proxy}")

    try:
        r = requests.get(
            query_url,
            headers=headers,
            proxies=config.proxy,
            verify=False,
            timeout=(30, 60),
        )
        response = r.json()
        image_items = []
        if "photos" not in response:
            logger.error(f"search images failed: {response}")
            return image_items
            
        photos = response["photos"]
        # loop through each image in the result
        for p in photos:
            # Check if we want all images or only specific types
            if image_type != "all":
                # For Pexels, we can't directly filter by animation vs photo in the API
                # We could potentially check file extension or other properties
                pass
                
            item = MaterialInfo()
            item.provider = "pexels"
            item.url = p["src"]["original"]
            item.width = p["width"]
            item.height = p["height"]
            item.type = MaterialType.image
            image_items.append(item)
            
        return image_items
    except Exception as e:
        logger.error(f"search images failed: {str(e)}")

    return []


def search_images_pixabay(
    search_term: str,
    image_aspect: VideoAspect = VideoAspect.portrait,
    image_type: Literal["all", "photo", "animation"] = "all",
    per_page: int = 40,
) -> List[MaterialInfo]:
    api_key = get_api_key("pixabay_api_keys")
    
    # Build URL
    params = {
        "q": search_term,
        "per_page": per_page,
        "key": api_key,
    }
    
    # Add image_type filter if specified
    if image_type == "animation":
        params["image_type"] = "animation"
    elif image_type == "photo":
        params["image_type"] = "photo"
    
    query_url = f"https://pixabay.com/api/?{urlencode(params)}"
    logger.info(f"searching images: {query_url}, with proxies: {config.proxy}")

    try:
        r = requests.get(
            query_url, proxies=config.proxy, verify=False, timeout=(30, 60)
        )
        response = r.json()
        image_items = []
        if "hits" not in response:
            logger.error(f"search images failed: {response}")
            return image_items
            
        images = response["hits"]
        # loop through each image in the result
        for img in images:
            item = MaterialInfo()
            item.provider = "pixabay"
            item.url = img["largeImageURL"]
            item.width = img["imageWidth"]
            item.height = img["imageHeight"]
            item.type = MaterialType.image
            image_items.append(item)
            
        return image_items
    except Exception as e:
        logger.error(f"search images failed: {str(e)}")

    return []


def save_video(video_url: str, save_dir: str = "") -> str:
    if not save_dir:
        save_dir = utils.storage_dir("cache_videos")

    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    url_without_query = video_url.split("?")[0]
    url_hash = utils.md5(url_without_query)
    video_id = f"vid-{url_hash}"
    video_path = f"{save_dir}/{video_id}.mp4"

    # if video already exists, return the path
    if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
        logger.info(f"video already exists: {video_path}")
        return video_path

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }

    # if video does not exist, download it
    with open(video_path, "wb") as f:
        f.write(
            requests.get(
                video_url,
                headers=headers,
                proxies=config.proxy,
                verify=False,
                timeout=(60, 240),
            ).content
        )

    if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
        try:
            clip = VideoFileClip(video_path)
            duration = clip.duration
            fps = clip.fps
            clip.close()
            if duration > 0 and fps > 0:
                return video_path
        except Exception as e:
            try:
                os.remove(video_path)
            except Exception:
                pass
            logger.warning(f"invalid video file: {video_path} => {str(e)}")
    return ""


def save_image(image_url: str, save_dir: str = ""):
    """Save an image to disk"""
    if not save_dir:
        save_dir = utils.storage_dir("images")

    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    url_without_query = image_url.split("?")[0]
    url_hash = utils.md5(url_without_query)
    image_id = f"img-{url_hash}"
    image_path = f"{save_dir}/{image_id}.jpg"

    # if image already exists, return the path
    if os.path.exists(image_path) and os.path.getsize(image_path) > 0:
        logger.info(f"image already exists: {image_path}")
        return image_path

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }

    # if image does not exist, download it
    try:
        response = requests.get(
            image_url,
            headers=headers,
            proxies=config.proxy,
            verify=False,
            timeout=(30, 60),
        )
        
        if response.status_code == 200:
            # Verify it's a valid image
            try:
                img = Image.open(io.BytesIO(response.content))
                img.save(image_path)
                return image_path
            except Exception as e:
                logger.warning(f"invalid image file: {image_path} => {str(e)}")
                return ""
    except Exception as e:
        logger.error(f"failed to download image: {image_url} => {str(e)}")
        
    return ""


def save_material(material_url: str, save_dir: str = "", material_type: MaterialType = MaterialType.video):
    """Save a material (video or image) to disk"""
    if material_type == MaterialType.video:
        return save_video(material_url, save_dir)
    else:
        return save_image(material_url, save_dir)


def download_materials(
    task_id: str,
    search_terms: List[str],
    source: str = "pexels",
    material_type: MaterialType = MaterialType.video,
    material_aspect: VideoAspect = VideoAspect.portrait,
    video_contact_mode: VideoConcatMode = VideoConcatMode.random,
    audio_duration: float = 0.0,
    max_clip_duration: int = 5,
    image_count: int = 20,
    image_type: str = "all",
) -> List[str]:
    """Download materials (videos or images) based on search terms"""
    if material_type == MaterialType.video:
        return download_videos(
            task_id=task_id,
            search_terms=search_terms,
            source=source,
            video_aspect=material_aspect,
            video_contact_mode=video_contact_mode,
            audio_duration=audio_duration,
            max_clip_duration=max_clip_duration,
        )
    else:
        return download_images(
            task_id=task_id,
            search_terms=search_terms,
            source=source,
            image_aspect=material_aspect,
            image_count=image_count,
            image_type=image_type,
        )


def download_images(
    task_id: str,
    search_terms: List[str],
    source: str = "pexels",
    image_aspect: VideoAspect = VideoAspect.portrait,
    image_count: int = 20,
    image_type: str = "all",
) -> List[str]:
    """Download images based on search terms"""
    valid_image_items = []
    valid_image_urls = []
    search_images = search_images_pexels
    if source == "pixabay":
        search_images = search_images_pixabay

    for search_term in search_terms:
        image_items = search_images(
            search_term=search_term,
            image_aspect=image_aspect,
            image_type=image_type,
        )
        logger.info(f"found {len(image_items)} images for '{search_term}'")

        for item in image_items:
            if item.url not in valid_image_urls:
                valid_image_items.append(item)
                valid_image_urls.append(item.url)

    logger.info(f"found total images: {len(valid_image_items)}")
    image_paths = []

    material_directory = config.app.get("material_directory", "").strip()
    if material_directory == "task":
        material_directory = utils.task_dir(task_id)
    elif material_directory and not os.path.isdir(material_directory):
        material_directory = ""

    # Shuffle the images to get a good mix
    random.shuffle(valid_image_items)

    # Limit to the requested number of images
    count = min(image_count, len(valid_image_items))
    for i in range(count):
        item = valid_image_items[i]
        try:
            logger.info(f"downloading image: {item.url}")
            saved_image_path = save_material(
                material_url=item.url, save_dir=material_directory, material_type=item.type
            )
            if saved_image_path:
                logger.info(f"image saved: {saved_image_path}")
                image_paths.append(saved_image_path)
        except Exception as e:
            logger.error(f"failed to download image: {utils.to_json(item)} => {str(e)}")
    
    logger.success(f"downloaded {len(image_paths)} images")
    return image_paths


def download_videos(
    task_id: str,
    search_terms: List[str],
    source: str = "pexels",
    video_aspect: VideoAspect = VideoAspect.portrait,
    video_contact_mode: VideoConcatMode = VideoConcatMode.random,
    audio_duration: float = 0.0,
    max_clip_duration: int = 5,
) -> List[str]:
    valid_video_items = []
    valid_video_urls = []
    found_duration = 0.0
    search_videos = search_videos_pexels
    if source == "pixabay":
        search_videos = search_videos_pixabay

    for search_term in search_terms:
        video_items = search_videos(
            search_term=search_term,
            minimum_duration=max_clip_duration,
            video_aspect=video_aspect,
        )
        logger.info(f"found {len(video_items)} videos for '{search_term}'")

        for item in video_items:
            if item.url not in valid_video_urls:
                valid_video_items.append(item)
                valid_video_urls.append(item.url)
                found_duration += item.duration

    logger.info(
        f"found total videos: {len(valid_video_items)}, required duration: {audio_duration} seconds, found duration: {found_duration} seconds"
    )
    video_paths = []

    material_directory = config.app.get("material_directory", "").strip()
    if material_directory == "task":
        material_directory = utils.task_dir(task_id)
    elif material_directory and not os.path.isdir(material_directory):
        material_directory = ""

    if video_contact_mode.value == VideoConcatMode.random.value:
        random.shuffle(valid_video_items)

    total_duration = 0.0
    for item in valid_video_items:
        try:
            logger.info(f"downloading video: {item.url}")
            saved_video_path = save_material(
                material_url=item.url, save_dir=material_directory, material_type=item.type
            )
            if saved_video_path:
                logger.info(f"video saved: {saved_video_path}")
                video_paths.append(saved_video_path)
                seconds = min(max_clip_duration, item.duration)
                total_duration += seconds
                if total_duration > audio_duration:
                    logger.info(
                        f"total duration of downloaded videos: {total_duration} seconds, skip downloading more"
                    )
                    break
        except Exception as e:
            logger.error(f"failed to download video: {utils.to_json(item)} => {str(e)}")
    logger.success(f"downloaded {len(video_paths)} videos")
    return video_paths


if __name__ == "__main__":
    # Test video download
    download_videos(
        "test123", ["Money Exchange Medium"], audio_duration=100, source="pixabay"
    )
    
    # Test image download
    # download_images(
    #     "test123", ["Money Exchange Medium"], source="pixabay", image_count=10
    # )
