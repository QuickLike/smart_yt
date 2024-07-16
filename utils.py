def get_video_id_from_url(url):
    video_id = None
    if 'youtu.be' in url:
        video_id = url.split('/')[-1].split('?')[0]
    elif 'youtube.com' in url:
        query_string = url.split('?')[1]
        video_id = query_string.split('=')[1]
    return video_id
