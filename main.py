import time
import curses
import asyncio
import os
from random import randint, choice
from itertools import cycle
from statistics import median

TIC_TIMEOUT = 0.1
SS_SPEED = 10

SPACE_KEY_CODE = 32
LEFT_KEY_CODE = 260
RIGHT_KEY_CODE = 261
UP_KEY_CODE = 259
DOWN_KEY_CODE = 258


class Phase():
    def __init__(self, row, column, symbol, delay, brightness):
        self.row = row
        self.column = column
        self.symbol = symbol
        self.delay = delay
        self.brightness = brightness

    def __await__(self):
        return (yield self)


async def blink(
        row, column, symbol='*', animation_schema=(2, 0.3, 0.5, 0.3)
        ):
    while True:
        await Phase(row, column, symbol, animation_schema[0], curses.A_DIM)
        await Phase(row, column, symbol, animation_schema[1], curses.A_NORMAL)
        await Phase(row, column, symbol, animation_schema[2], curses.A_BOLD)
        await Phase(row, column, symbol, animation_schema[3], curses.A_NORMAL)


async def fire(canvas, start_row, start_column, rows_speed=-0.3, columns_speed=0.0):
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


def draw_frame(canvas, start_row, start_column, text, negative=False):
    """Draw multiline text fragment on canvas, erase text instead of drawing if negative=True is specified."""

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

            # Check that current position it is not in a lower right corner of the window
            # Curses will raise exception in that case. Don`t ask why…
            # https://docs.python.org/3/library/curses.html#curses.window.addch
            if row == rows_number - 1 and column == columns_number - 1:
                continue

            symbol = symbol if not negative else ' '
            canvas.addch(row, column, symbol)


def read_controls(canvas):
    """Read keys pressed and returns tuple witl controls state."""
    
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
    """Calculate size of multiline text fragment, return pair — number of rows and colums."""
    
    lines = text.splitlines()
    rows = len(lines)
    columns = max([len(line) for line in lines])
    return rows, columns


async def animate_spaceship(canvas, start_row:int, start_column:int, frame:str):    
    draw_frame(canvas, start_row, start_column, frame, negative=False)
    await asyncio.sleep(0)
    draw_frame(canvas, start_row, start_column, frame, negative=True)
    await asyncio.sleep(0)


def draw(canvas):
    with open(os.path.join('frames', 'rocket_frame_1.txt')) as file:
        frame1 = file.read()
    with open(os.path.join('frames', 'rocket_frame_2.txt')) as file:
        frame2 = file.read()
    frames = cycle((frame1, frame2))
        
    
    canvas.border()
    curses.curs_set(False)
    canvas.nodelay(True)
    screen_height, screen_width = canvas.getmaxyx()
    stars = []

    for _ in range(100):
        stars.append(
            blink(
                randint(2, screen_height - 2),
                randint(2, screen_width - 2),
                symbol=choice(list('+*.:')),
                animation_schema=(
                    TIC_TIMEOUT * randint(5, 25),
                    TIC_TIMEOUT * randint(2, 8),
                    TIC_TIMEOUT * randint(3, 10),
                    TIC_TIMEOUT * randint(2, 8),
                ),
            )
        )

    star_data = [[star, star.send(None)] for star in stars]
    ss_raw = screen_height / 2
    ss_column = screen_width / 2
    shots = []
    
    while True:
        rows_direction, columns_direction, space_pressed = read_controls(canvas)
        frame = next(frames)
        frame_rows, frame_cols = get_frame_size(frame)
        ss_raw = median((
            1, 
            ss_raw + rows_direction * TIC_TIMEOUT * SS_SPEED, 
            screen_height - frame_rows - 1
        ))
        ss_column = median((
            1, 
            ss_column + columns_direction * TIC_TIMEOUT * SS_SPEED, 
            screen_width - frame_cols - 1
        ))
        shots.append(animate_spaceship(canvas, round(ss_raw), round(ss_column), frame))
        
        if randint(1, 100) < 10:
            shots.append(fire(
                canvas,
                round(ss_raw),
                round(ss_column) + 2,
                rows_speed=choice([-5, -4, -3, -2, 2, 3, 4, 5]) * TIC_TIMEOUT,
                columns_speed=choice([-5, -4, -3, -2, 2, 3, 4, 5]) * TIC_TIMEOUT
            ))
        for _, phase in star_data:
            canvas.addstr(
                phase.row, phase.column, phase.symbol, phase.brightness
                )
            phase.delay -= TIC_TIMEOUT
        
        for shot in shots.copy():
            try:
                shot.send(None)
            except StopIteration:
                shots.remove(shot)
                
        canvas.refresh()


        change_phase = [[star, phase] for star, phase in star_data if
                        phase.delay <= 0]
        star_data = [[star, phase] for star, phase in star_data if
                     phase.delay > 0]
        for star, _ in change_phase:
            star_data.append([star, star.send(None)])

        time.sleep(TIC_TIMEOUT)


if __name__ == '__main__':
    curses.update_lines_cols()
    curses.wrapper(draw)
