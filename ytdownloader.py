import imghdr
import os
import re
import subprocess

import requests
from yt_dlp import YoutubeDL
import ffmpeg
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB


VIDEO_SAVE_PATH = 'videos'
AUDIO_SAVE_PATH = 'audios'


def download_video(url):
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'outtmpl': f'{VIDEO_SAVE_PATH}/%(title)s.%(ext)s',
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            info_dict = ydl.extract_info(url, download=False)
            video_filename = ydl.prepare_filename(info_dict)
            return video_filename
    except Exception as e:
        print(f"Ошибка при загрузке видео: {e}")
        return


def convert_to_mp3(input_file, output_file):
    try:
        subprocess.run(['ffmpeg', '-i', input_file, output_file], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при конвертации файла: {e}")
        return False
    return True


def download_audio(url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{AUDIO_SAVE_PATH}/%(title)s.%(ext)s',
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            audio_title = info_dict.get('title', None)
            artist = info_dict.get('uploader', None)
            album = info_dict.get('album', None)
            thumbnail_url = info_dict.get('thumbnail', None)
            original_filename = ydl.prepare_filename(info_dict)

            # Определяем расширение исходного файла
            file_extension = original_filename.split('.')[-1]
            temp_mp3_filename = original_filename.replace(f'.{file_extension}', '_temp.mp3')
            final_mp3_filename = original_filename.replace(f'.{file_extension}', '.mp3')

            if os.path.exists(original_filename):
                if not convert_to_mp3(original_filename, temp_mp3_filename):
                    return None
                os.rename(temp_mp3_filename, final_mp3_filename)
                os.remove(original_filename)
            else:
                print(f"Файл {original_filename} не найден.")
                return None

            if thumbnail_url:
                thumbnail_path = f"{AUDIO_SAVE_PATH}/thumbs/{audio_title}.jpg"

                # Скачивание миниатюры
                response = requests.get(thumbnail_url)
                if response.status_code == 200:
                    with open(thumbnail_path, 'wb') as f:
                        f.write(response.content)

                    # Проверка формата изображения
                    if imghdr.what(thumbnail_path) in ['jpeg', 'png']:
                        audio = MP3(final_mp3_filename, ID3=ID3)
                        audio.tags.add(
                            APIC(
                                encoding=3,  # 3 is for utf-8
                                mime='image/jpeg',  # image/jpeg or image/png
                                type=3,  # 3 is for the cover image
                                desc='Cover',
                                data=open(thumbnail_path, 'rb').read()
                            )
                        )
                        audio.tags.add(TIT2(encoding=3, text=audio_title))
                        if artist:
                            audio.tags.add(TPE1(encoding=3, text=artist))
                        if album:
                            audio.tags.add(TALB(encoding=3, text=album))
                        audio.save()
                    else:
                        print("Миниатюра не является изображением.")
                else:
                    print("Ошибка при скачивании миниатюры.")

            return final_mp3_filename, audio_title, artist
    except Exception as e:
        print(f"Ошибка при загрузке аудио: {e}")
        return None


def get_info(url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            audio_title = info_dict.get('title', None)
            artist = info_dict.get('uploader', None)
            album = info_dict.get('album', None)
            thumbnail_url = info_dict.get('thumbnail', None)
            return {
                'title': audio_title,
                'artist': artist,
                'thumbnail': thumbnail_url
            }
    except Exception as e:
        print(e)
        return
