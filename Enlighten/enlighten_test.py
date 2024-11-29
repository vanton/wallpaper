import asyncio
import random
import enlighten

from Enlighten.gen_colors import generate_colors

manager = enlighten.get_manager()
chunk_size = 64 * 1024  # 64 KiB
max_concurrent = 4
bar_format = (
    manager.term.blue
    + "{desc}{desc_pad}{percentage:3.0f}%|{bar}| "
    + "{count:!.2j}{unit} / {total:!.2j}{unit} "
    + manager.term.red
    + "[{elapsed}<{eta}, {rate:!.2j}{unit}/s]"
)
color_index = 0


def get_task(color=None):
    global color_index
    size = random.uniform(1.0, 10.0) * 2**20  # 1-10 MiB (float)
    colors = generate_colors(12)
    color = color or colors[color_index % len(colors)]
    color_index += 1
    return (
        manager.counter(
            total=size,
            desc="Downloading",
            unit="B",
            bar_format=bar_format,
            color=color,
        ),
        size,
    )


async def download(task):
    p_bar, bytes_left = task
    try:
        while bytes_left > 0:
            await asyncio.sleep(random.uniform(0.01, 0.10))
            next_chunk = min(chunk_size, bytes_left)
            p_bar.update(next_chunk)
            bytes_left -= next_chunk
        return task
    except Exception as e:
        raise Exception(f"Download failed: {str(e)}")


async def download_all(tasks):
    async def bounded_download(semaphore, task):
        async with semaphore:
            return await download(task)

    sem = asyncio.Semaphore(max_concurrent)
    download_tasks = [
        asyncio.create_task(bounded_download(sem, task)) for task in tasks
    ]

    try:
        results = await asyncio.gather(*download_tasks)
        return results
    except Exception as e:
        print(f"Error during download: {str(e)}")
        return []


if __name__ == "__main__":
    p_bars = [get_task() for _ in range(30)]
    asyncio.run(download_all(p_bars))
