import time
import curses
import asyncio
import os
from random import randint, choice
from itertools import cycle
from statistics import median

TIC_TIMEOUT = 0.1
SS_SPEED = 10
TOTAL_STARS = 100
SHOT_PROBABILITY = 10
GARBAGE_PROBABILITY = 5
SHELL_SPEED = 5
SCREEN_BORDER_WIDTH = 1

SPACE_KEY_CODE = 32
LEFT_KEY_CODE = 260
RIGHT_KEY_CODE = 261
UP_KEY_CODE = 259
DOWN_KEY_CODE = 258


async def blink(
        canvas, row, column, symbol='*', animation_schema=(2, 0.3, 0.5, 0.3)
        ):
    while True:
        for delay, brightness in zip(animation_schema, (
                curses.A_DIM, curses.A_NORMAL, curses.A_BOLD, curses.A_NORMAL
        )):
            canvas.addstr(row, column, symbol, brightness)
            while delay > 0:
                delay -= TIC_TIMEOUT
                await asyncio.sleep(0)


async def fire(
        canvas, start_row, start_column, rows_speed=-0.3, columns_speed=0.0
):
    """Display animation of gun shot, direction and speed can be specified."""

    row, column = start_row, start_column

    canvas.addstr(round(row), round(column), '*')
    await asyncio.sleep(0)

    canvas.addstr(round(row), round(column), 'O')
    await asyncio.sleep(0)
    canvas.addstr(round(row), round(column), ' ')

    row += rows_speed
    column += columns_speed

    symbol = '-' if columns_speed else '|'

    rows, columns = canvas.getmaxyx()
    max_row, max_column = rows - 2, columns - 2

    curses.beep()

    while 1 < row < max_row and 1 < column < max_column:
        canvas.addstr(round(row), round(column), symbol)
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed


async def fly_garbage(canvas, column, garbage_frame, speed=0.5):
    """Animate garbage, flying from top to bottom.
    Column position will stay same, as specified on start."""
    rows_number, columns_number = canvas.getmaxyx()

    column = max(column, 0)
    column = min(column, columns_number - 1)

    row = 0

    while row < rows_number:
        draw_frame(canvas, row, column, garbage_frame)
        await asyncio.sleep(0)
        draw_frame(canvas, row, column, garbage_frame, negative=True)
        row += speed


def draw_frame(canvas, start_row, start_column, text, negative=False):
    """Draw multiline text fragment on canvas,
    erase text instead of drawing if negative=True is specified."""

    rows_number, columns_number = canvas.getmaxyx()

    for row, line in enumerate(text.splitlines(), round(start_row)):
        if row < 0:
            continue

        if row >= rows_number:
            break

        for column, symbol in enumerate(line, round(start_column)):
            if column < 0:
                continue

            if column >= columns_number:
                break

            if symbol == ' ':
                continue

            # Check that current position it is not in a lower right corner of
            # the window. Curses will raise exception in that case.
            # Don`t ask why…
            # https://docs.python.org/3/library/curses.html#curses.window.addch
            if row == rows_number - 1 and column == columns_number - 1:
                continue

            symbol = symbol if not negative else ' '
            canvas.addch(row, column, symbol)


def read_controls(canvas):
    """Read keys pressed and returns tuple with controls state."""

    rows_direction = columns_direction = 0
    space_pressed = False

    while True:
        pressed_key_code = canvas.getch()

        if pressed_key_code == -1:
            # https://docs.python.org/3/library/curses.html#curses.window.getch
            break

        if pressed_key_code == UP_KEY_CODE:
            rows_direction = -1

        if pressed_key_code == DOWN_KEY_CODE:
            rows_direction = 1

        if pressed_key_code == RIGHT_KEY_CODE:
            columns_direction = 1

        if pressed_key_code == LEFT_KEY_CODE:
            columns_direction = -1

        if pressed_key_code == SPACE_KEY_CODE:
            space_pressed = True

    return rows_direction, columns_direction, space_pressed


def get_frame_size(text):
    """Calculate size of multiline text fragment, return pair —
    number of rows and columns."""

    lines = text.splitlines()
    rows = len(lines)
    columns = max([len(line) for line in lines])
    return rows, columns


async def animate_spaceship(
        canvas, start_row: int, start_column: int, frames: list, loop: list
):
    screen_height, screen_width = canvas.getmaxyx()
    ss_raw, ss_column = start_row, start_column
    for frame in cycle(frames):
        rows_direction, columns_direction, _ = read_controls(canvas)
        frame_rows, frame_cols = get_frame_size(frame)
        ss_raw = median(
            (
                SCREEN_BORDER_WIDTH,
                ss_raw + rows_direction * TIC_TIMEOUT * SS_SPEED,
                screen_height - frame_rows - SCREEN_BORDER_WIDTH
            )
        )
        ss_column = median(
            (
                SCREEN_BORDER_WIDTH,
                ss_column + columns_direction * TIC_TIMEOUT * SS_SPEED,
                screen_width - frame_cols - SCREEN_BORDER_WIDTH
            )
        )

        # беспорядочная стрельба
        if randint(1, 100) < SHOT_PROBABILITY:
            rows_speed = randint(-SHELL_SPEED, SHELL_SPEED) * TIC_TIMEOUT
            columns_speed = (SHELL_SPEED ** 2 - rows_speed ** 2) ** 0.5
            loop.append(
                fire(
                    canvas,
                    round(ss_raw),
                    round(ss_column) + 2,
                    rows_speed=rows_speed,
                    columns_speed=columns_speed
                )
            )

        draw_frame(
            canvas, round(ss_raw), round(ss_column), frame, negative=False
        )
        await asyncio.sleep(0)
        draw_frame(
            canvas, round(ss_raw), round(ss_column), frame, negative=True
            )


def draw(canvas):
    frames = []
    for filename in ('rocket_frame_1.txt', 'rocket_frame_2.txt'):
        with open(os.path.join('frames', filename)) as file:
            frames.append(file.read().rstrip())

    canvas.border()
    curses.curs_set(False)
    canvas.nodelay(True)
    screen_height, screen_width = canvas.getmaxyx()
    sprites = []

    for _ in range(TOTAL_STARS):
        sprites.append(
            blink(
                canvas,
                randint(2, screen_height - 2),
                randint(2, screen_width - 2),
                symbol=choice(list('+*.:°')),
                animation_schema=(
                    TIC_TIMEOUT * randint(5, 25),
                    TIC_TIMEOUT * randint(2, 8),
                    TIC_TIMEOUT * randint(3, 10),
                    TIC_TIMEOUT * randint(2, 8),
                ),
            )
        )

    sprites.append(animate_spaceship(
        canvas, screen_height / 2, screen_width / 2, frames, sprites
    ))

    garbage_frames = []
    for filename in os.listdir('frames/garbage'):
        with open(os.path.join('frames/garbage', filename)) as file:
            garbage_frames.append(file.read().rstrip())

    while True:
        for sprite in sprites.copy():
            try:
                sprite.send(None)
            except StopIteration:
                sprites.remove(sprite)

        # выброс случайного мусора
        if randint(1, 100) < GARBAGE_PROBABILITY:
            sprites.append(fly_garbage(canvas,
                                       randint(2, screen_width - 2),
                                       choice(garbage_frames)))

        canvas.refresh()
        time.sleep(TIC_TIMEOUT)


if __name__ == '__main__':
    curses.update_lines_cols()
    curses.wrapper(draw)
