import time
import curses
import asyncio
import os
from random import randint, choice
from itertools import cycle
from statistics import median

import config
from physics import update_speed
from curses_tools import draw_frame, get_frame_size, read_controls
from obstacles import Obstacle
from explosion import explode


async def sleep(tics=1):
    for _ in range(tics):
        await asyncio.sleep(0)


async def blink(
        canvas, row, column, symbol='*', animation_schema=(2, 0.3, 0.5, 0.3)
        ):
    while True:
        for delay, brightness in zip(animation_schema, (
                curses.A_DIM, curses.A_NORMAL, curses.A_BOLD, curses.A_NORMAL
        )):
            canvas.addstr(row, column, symbol, brightness)
            await sleep(int(delay / config.TIC_TIMEOUT))


async def fire(
        canvas, start_row, start_column, rows_speed=-0.5, columns_speed=0.0
):
    """Display animation of gun shot, direction and speed can be specified."""

    row, column = start_row, start_column

    canvas.addstr(round(row), round(column), '*')
    await sleep(1)

    canvas.addstr(round(row), round(column), 'O')
    await sleep(1)
    canvas.addstr(round(row), round(column), ' ')

    row += rows_speed
    column += columns_speed

    symbol = '-' if columns_speed else '|'

    rows, columns = canvas.getmaxyx()
    max_row, max_column = rows - 2, columns - 2

    curses.beep()

    while 1 < row < max_row and 1 < column < max_column:
        for obstacle in obstacles.copy():
            if obstacle.has_collision(row, column):
                obstacles.remove(obstacle)
                sprites.append(
                    explode(
                        canvas,
                        obstacle.row + obstacle.rows_size // 2,
                        obstacle.column + obstacle.columns_size // 2,
                    )
                )
                return

        canvas.addstr(round(row), round(column), symbol)
        await sleep(1)
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed


async def fly_garbage(canvas, column, garbage_frame, speed=0.3):
    """Animate garbage, flying from top to bottom.
    Column position will stay same, as specified on start."""
    rows_number, columns_number = canvas.getmaxyx()

    rows_size, columns_size = get_frame_size(garbage_frame)
    obstacle = Obstacle(0, column, rows_size, columns_size)
    obstacles.append(obstacle)

    obstacle.column = max(column, 0)
    obstacle.column = min(column, columns_number - 1)

    while obstacle.row < rows_number:
        if obstacle not in obstacles:
            return
        draw_frame(canvas, obstacle.row, obstacle.column, garbage_frame)
        await sleep(1)
        draw_frame(
            canvas, obstacle.row, obstacle.column, garbage_frame, negative=True
            )
        obstacle.row += speed
    obstacles.remove(obstacle)


async def fill_orbit_with_garbage(canvas):
    screen_height, screen_width = canvas.getmaxyx()
    garbage_frames = []
    for filename in os.listdir('frames/garbage'):
        with open(os.path.join('frames/garbage', filename)) as file:
            garbage_frames.append(file.read().rstrip())
    while not game_over:
        await sleep(randint(config.MIN_GARBAGE_DELAY, config.MAX_GARBAGE_DELAY))
        sprites.append(
            fly_garbage(
                canvas,
                randint(2, screen_width - 2),
                choice(garbage_frames),
            )
        )


async def animate_spaceship(
        canvas, start_row: int, start_column: int, frames: list
):
    screen_height, screen_width = canvas.getmaxyx()
    ss_raw, ss_column = start_row, start_column
    row_speed, column_speed = 0, 0
    for frame in cycle(frames):
        rows_direction, columns_direction, shot = read_controls(canvas)
        row_speed, column_speed = update_speed(
            row_speed, column_speed, rows_direction, columns_direction
        )
        frame_rows, frame_cols = get_frame_size(frame)
        ss_raw = median(
            (
                config.SCREEN_BORDER_WIDTH,
                ss_raw + row_speed * config.TIC_TIMEOUT * config.SS_SPEED,
                screen_height - frame_rows - config.SCREEN_BORDER_WIDTH
            )
        )
        ss_column = median(
            (
                config.SCREEN_BORDER_WIDTH,
                ss_column + column_speed * config.TIC_TIMEOUT * config.SS_SPEED,
                screen_width - frame_cols - config.SCREEN_BORDER_WIDTH
            )
        )

        if shot:
            sprites.append(fire(
                canvas,
                round(ss_raw),
                round(ss_column) + 2,
                rows_speed=-1,
                columns_speed=0
            ))

        draw_frame(
            canvas, round(ss_raw), round(ss_column), frame, negative=False
        )
        
        for obstacle in obstacles:
            if obstacle.has_collision(ss_raw, ss_column, *get_frame_size(frame)):
                sprites.append(set_game_over(canvas))
                return
        
        await sleep(2)
        draw_frame(
            canvas, round(ss_raw), round(ss_column), frame, negative=True
            )


async def set_game_over(canvas):
    global game_over
    game_over = True
    screen_height, screen_width = canvas.getmaxyx()
    with open(os.path.join('frames', 'game_over.txt')) as file:
        frame = file.read().rstrip()
    banner_rows, banner_columns = get_frame_size(frame)
    while True:
        draw_frame(
            canvas, 
            (screen_height - banner_rows) // 2,
            (screen_width - banner_columns) // 2,
            frame
        )
        await sleep(1)


async def count_year(canvas):
    global year
    screen_height, screen_width = canvas.getmaxyx()
    year_canvas = canvas.derwin(
        1,
        5,
        screen_height - config.SCREEN_BORDER_WIDTH - 1,
        1
    )
    while True:
        year_canvas.addstr(0, 0, str(year))
        year_canvas.refresh()
        await sleep(int(config.YEAR_DURATION_SEC / config.TIC_TIMEOUT))
        year += 1


def draw(canvas):
    frames = []
    for filename in os.listdir('frames/rocket'):
        with open(os.path.join('frames/rocket', filename)) as file:
            frames.append(file.read().rstrip())

    canvas.border()
    curses.curs_set(False)
    canvas.nodelay(True)
    screen_height, screen_width = canvas.getmaxyx()

    for _ in range(config.TOTAL_STARS):
        sprites.append(
            blink(
                canvas,
                randint(2, screen_height - 2),
                randint(2, screen_width - 2),
                symbol=choice(list('+*.:°')),
                animation_schema=(
                    config.TIC_TIMEOUT * randint(5, 25),
                    config.TIC_TIMEOUT * randint(2, 8),
                    config.TIC_TIMEOUT * randint(3, 10),
                    config.TIC_TIMEOUT * randint(2, 8),
                ),
            )
        )

    sprites.append(animate_spaceship(
        canvas, screen_height / 2, screen_width / 2, frames
    ))

    sprites.append(fill_orbit_with_garbage(canvas))
    sprites.append(count_year(canvas))

    while True:
        for sprite in sprites.copy():
            try:
                sprite.send(None)
            except StopIteration:
                sprites.remove(sprite)

        canvas.refresh()
        time.sleep(config.TIC_TIMEOUT)


if __name__ == '__main__':
    year = 1957
    game_over = False
    sprites = []
    obstacles = []
    curses.update_lines_cols()
    curses.wrapper(draw)
