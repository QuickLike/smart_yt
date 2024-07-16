import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from environs import Env
from pytube import Playlist

from database import Database
from utils import get_video_id_from_url
from ytdownloader import download_video, download_audio, get_info

env = Env()
env.read_env()
BOT_TOKEN = env.str("BOT_TOKEN")

dp = Dispatcher()
db = Database()
bot = Bot(token=BOT_TOKEN)

playlist_pattern = (r'^(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:playlist\?list=)|youtu\.be\/playlists\/)(['
                    r'a-zA-Z0-9_-]+)')
video_pattern = (r'^(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:watch\?v=|embed\/|v\/|shorts\/)|youtu\.be\/)(['
                 r'a-zA-Z0-9_-]{11})')


class DownloadCallbackData(CallbackData, prefix="download"):
    type: str
    url: str


@dp.message(Command('start'))
async def start(message: types.Message):
    await message.answer(
        text=('Добро пожаловать!\n\nБот умеет скачивать видео и аудио.'
              'Просто пришлите ссылку на видео или плейлист.'
              'Из плейлиста будут скачаны все аудио.'),
    )


@dp.message(Command('clear'))
async def cache_clear(message: types.Message):
    thumbs_path = 'audios/thumbs'
    thumbs = os.listdir(thumbs_path)
    full_size = sum([os.path.getsize(f"{thumbs_path}/{thumb}") for thumb in os.listdir(thumbs_path)])
    for thumb in thumbs:
        print(thumb.ljust(50), end=' ')
        print(f'{os.path.getsize(f"{thumbs_path}/{thumb}") / 10**5:.3f} МБ')
    print('-' * 60)
    await message.answer(f'Размер кэша составляет: {full_size / 10**5:.3f} МБ')
    print('Размер кэша составляет: '.ljust(51) + f'{full_size / 10**5:.3f} МБ')
    if full_size:
        try:
            [os.remove(f"{thumbs_path}/{thumb}") for thumb in thumbs]
            await message.answer('Успешно очищено✅')
            print('Успешно очищено')
        except Exception as e:
            await message.answer(
                text='<b>Возникла ошибка!</b>❌',
                parse_mode=ParseMode.HTML,
            )
            print(e)


@dp.message(F.text.regexp(playlist_pattern))
async def download_playlist(message: types.Message):
    link = Playlist(message.text)
    await message.answer(f'Количество видео в плейлисте {len(link.video_urls)}')
    await asyncio.sleep(1)
    message = await message.answer('Загружаю данные из плейлиста...')
    info = get_info(message.text)
    await message.delete()
    text = f"<b>Название:</b> <i>{info['title']}</i>\n<b>Автор:</b> <i>{info['artist']}</i>\n"
    await message.answer(text, parse_mode=ParseMode.HTML)
    for url in link.video_urls:
        info = get_info(url)
        text = (f"<b>Название:</b> <i>{info['title']}</i>\n<b>Автор:</b> <i>{info['artist']}</i>\n"
                f"<a href=\"{info['thumbnail']}\">&#32</a>\n\n"
                )
        await message.answer(text, parse_mode=ParseMode.HTML)
        file_url = url.split('=')[-1]
        filetype = 'audio'
        file_id = db.get_id(file_url, filetype)
        if file_id:
            await message.answer_audio(
                audio=file_id,
            )
        else:
            message = await message.answer('Загрузка началась...')
            filename, audio_title, artist = download_audio(file_url)
            if filename:
                db.insert(filename, file_url, filetype, audio_title, artist)
                try:
                    await message.delete()
                except Exception as e:
                    pass
                message = await message.answer(f'Аудиофайл загружен.')

                if os.path.exists(filename):
                    sent_message = await message.answer_audio(types.FSInputFile(filename))
                    # file_id = await bot.get_file(file_id)
                    db.update(file_url, filetype, sent_message.audio.file_id)
                    await message.delete()
                    os.remove(filename)
                else:
                    await message.answer('Файл не найден на сервере после загрузки.')
            else:
                await message.answer('Ошибка при загрузке файла.')


@dp.message(F.text.regexp(video_pattern))
async def select_type(message: types.Message):
    video_id = get_video_id_from_url(message.text)
    info = get_info(message.text)
    text = (f"<b>Название:</b> <i>{info['title']}</i>\n<b>Автор:</b> <i>{info['artist']}</i>\n"
            f"<a href=\"{info['thumbnail']}\">&#32</a>\n\n"
            f"<b>Выберите формат:</b>")
    if video_id:
        await message.answer(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text='Видео📹',
                            callback_data=DownloadCallbackData(type='video', url=video_id).pack()
                        ),
                        InlineKeyboardButton(
                            text='Аудио🎧',
                            callback_data=DownloadCallbackData(type='audio', url=video_id).pack()
                        ),
                    ],
                ]
            )
        )
    else:
        await message.answer(
            text='Не удалось извлечь идентификатор видео из ссылки. Попробуйте еще раз.'
        )


@dp.callback_query(DownloadCallbackData.filter())
async def download(callback: types.CallbackQuery, callback_data: DownloadCallbackData):
    filetype = callback_data.type
    file_url = callback_data.url
    send = {
        'video': callback.message.answer_video,
        'audio': callback.message.answer_audio,
    }
    file_id = db.get_id(file_url, filetype)
    if file_id:
        await send[filetype](**{filetype: file_id})
    else:
        message = await callback.message.answer('Загрузка началась...')
        filename, audio_title, artist = download_audio(file_url)
        if filename:
            db.insert(
                path=filename,
                url=file_url,
                filetype=filetype,
                title=audio_title,
                author=artist
            )
            try:
                await message.delete()
            except Exception as e:
                pass
            message = await callback.message.answer(f'Файл загружен.')

            if os.path.exists(filename):
                sent_message = await send[filetype](types.FSInputFile(filename))
                file_id = sent_message.audio.file_id if filetype == 'audio' else sent_message.video.file_id
                # file_id = await bot.get_file(file_id)
                db.update(file_url, filetype, file_id)
                await message.delete()
                os.remove(filename)
            else:
                await callback.message.answer('Файл не найден на сервере после загрузки.')
        else:
            await callback.message.answer('Ошибка при загрузке файла.')


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format=('%(asctime)s, '
                '%(levelname)s, '
                '%(funcName)s, '
                '%(lineno)d, '
                '%(message)s'
                ),
        encoding='UTF-8',
        handlers=[logging.FileHandler(__file__ + '.log'),
                  logging.StreamHandler(sys.stdout)]
    )
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
