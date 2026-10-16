import math
import random
from array import array

import pygame

from .hole import Hole


DARK_BROWN = (60, 40, 20)
MOLE_BROWN = (140, 95, 55)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRASS_GREEN = (120, 170, 90)
GOLD = (255, 215, 80)


class GameEngine:
    DIFFICULTIES = {
        "Easy": {"spawn_chance": 0.012, "mole_frames": 65},
        "Medium": {"spawn_chance": 0.020, "mole_frames": 45},
        "Hard": {"spawn_chance": 0.032, "mole_frames": 30},
    }

    def __init__(self, width, height, rows=3, cols=3):
        self.width = width
        self.height = height
        self.rows = rows
        self.cols = cols

        pygame.font.init()

        self.font = pygame.font.SysFont("Arial", 27)
        self.title_font = pygame.font.SysFont("Arial", 42, bold=True)
        self.button_font = pygame.font.SysFont("Arial", 25, bold=True)
        self.small_font = pygame.font.SysFont("Arial", 19)

        self.sound_enabled = False
        self.hit_sound = None
        self.miss_sound = None
        self.end_sound = None
        self._init_sounds()

        self.difficulty = "Medium"
        self.state = "playing"
        self.score = 0
        self.misses = 0
        self.round_seconds = 30
        self.time_left_frames = self.round_seconds * 60
        self._end_sound_played = False

        self._create_holes()
        self._apply_difficulty()

    @property
    def game_over(self):
        return self.state == "game_over"

    def _create_holes(self):
        self.holes = []

        spacing_x = self.width // (self.cols + 1)
        spacing_y = (self.height - 80) // (self.rows + 1)

        for row in range(self.rows):
            for col in range(self.cols):
                center_x = spacing_x * (col + 1)
                center_y = 80 + spacing_y * (row + 1)
                self.holes.append(Hole(center_x, center_y, hit_size=64))

    def _apply_difficulty(self):
        settings = self.DIFFICULTIES[self.difficulty]
        self.spawn_chance = settings["spawn_chance"]
        self.mole_up_frames = settings["mole_frames"]

    def _init_sounds(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(
                    frequency=22050,
                    size=-16,
                    channels=1,
                    buffer=512,
                )

            sample_rate = 22050

            def make_tone(frequency, duration, volume=0.25):
                sample_count = int(sample_rate * duration)
                samples = array("h")

                for index in range(sample_count):
                    envelope = max(
                        0.0,
                        1.0 - index / sample_count,
                    )
                    value = int(
                        32767
                        * volume
                        * envelope
                        * math.sin(
                            2 * math.pi * frequency * index / sample_rate
                        )
                    )
                    samples.append(value)

                return pygame.mixer.Sound(buffer=samples.tobytes())

            self.hit_sound = make_tone(880, 0.09)
            self.miss_sound = make_tone(220, 0.12)
            self.end_sound = make_tone(440, 0.35, 0.3)
            self.sound_enabled = True

        except (pygame.error, OSError, RuntimeError):
            self.sound_enabled = False

    def _play_sound(self, sound):
        if self.sound_enabled and sound is not None:
            try:
                sound.play()
            except pygame.error:
                pass

    def _finish_round(self):
        if self.state != "playing":
            return

        self.state = "game_over"

        if not self._end_sound_played:
            self._play_sound(self.end_sound)
            self._end_sound_played = True

    def _start_round(self, difficulty):
        self.difficulty = difficulty
        self._apply_difficulty()

        self.score = 0
        self.misses = 0
        self.time_left_frames = self.round_seconds * 60
        self.state = "playing"
        self._end_sound_played = False

        for hole in self.holes:
            hole.active = False
            hole.timer = 0

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.state = "exit"
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.state = "exit"
                return

            if self.state == "game_over":
                if event.key == pygame.K_1:
                    self._start_round("Easy")
                elif event.key == pygame.K_2:
                    self._start_round("Medium")
                elif event.key == pygame.K_3:
                    self._start_round("Hard")
                elif event.key in (pygame.K_4, pygame.K_q):
                    self.state = "exit"
                return

        if self.state == "playing" and event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self._handle_click(event.pos)

        elif self.state == "game_over" and event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self._handle_menu_click(event.pos)

    def _handle_click(self, pos):
        active_hits = [
            hole
            for hole in self.holes
            if hole.active and hole.rect().collidepoint(pos)
        ]

        if active_hits:
            # Select only one hole for every click.
            target = min(
                active_hits,
                key=lambda hole: (
                    (hole.center_x - pos[0]) ** 2
                    + (hole.center_y - pos[1]) ** 2
                ),
            )

            if target.whack():
                self.score += 1
                self._play_sound(self.hit_sound)
                return

        self.misses += 1
        self._play_sound(self.miss_sound)

    def _menu_buttons(self):
        button_width = 300
        button_height = 48
        gap = 12
        start_y = 250

        buttons = []

        options = [
            ("Easy", "Easy"),
            ("Medium", "Medium"),
            ("Hard", "Hard"),
            ("Exit", "Exit"),
        ]

        for index, (label, action) in enumerate(options):
            rect = pygame.Rect(
                (self.width - button_width) // 2,
                start_y + index * (button_height + gap),
                button_width,
                button_height,
            )
            buttons.append((rect, label, action))

        return buttons

    def _handle_menu_click(self, pos):
        for rect, label, action in self._menu_buttons():
            if rect.collidepoint(pos):
                if action == "Exit":
                    self.state = "exit"
                else:
                    self._start_round(action)
                return

    def handle_input(self):
        pass

    def update(self):
        if self.state != "playing":
            return

        self.time_left_frames -= 1

        if self.time_left_frames <= 0:
            self.time_left_frames = 0
            self._finish_round()
            return

        for hole in self.holes:
            hole.update()

        for hole in self.holes:
            if not hole.active and random.random() < self.spawn_chance:
                hole.pop_up(self.mole_up_frames)

    def _draw_text(self, screen, text, font, color, center):
        surface = font.render(text, True, color)
        screen.blit(surface, surface.get_rect(center=center))

    def render(self, screen):
        screen.fill(GRASS_GREEN)

        if self.state == "game_over":
            self._render_game_over(screen)
            return

        for hole in self.holes:
            pygame.draw.circle(
                screen,
                DARK_BROWN,
                (hole.center_x, hole.center_y),
                40,
            )

            if hole.active:
                pygame.draw.circle(
                    screen,
                    MOLE_BROWN,
                    (hole.center_x, hole.center_y),
                    32,
                )

                pygame.draw.circle(
                    screen,
                    (245, 225, 190),
                    (hole.center_x - 10, hole.center_y - 5),
                    4,
                )

                pygame.draw.circle(
                    screen,
                    (245, 225, 190),
                    (hole.center_x + 10, hole.center_y - 5),
                    4,
                )

        score_text = self.font.render(
            f"Score: {self.score}",
            True,
            BLACK,
        )
        screen.blit(score_text, (10, 10))

        seconds_left = max(0, self.time_left_frames // 60)
        timer_text = self.font.render(
            f"Time: {seconds_left}s",
            True,
            BLACK,
        )
        screen.blit(
            timer_text,
            (self.width - timer_text.get_width() - 10, 10),
        )

        difficulty_text = self.small_font.render(
            f"Difficulty: {self.difficulty}",
            True,
            BLACK,
        )
        screen.blit(difficulty_text, (10, 48))

    def _render_game_over(self, screen):
        overlay = pygame.Surface(
            (self.width, self.height),
            pygame.SRCALPHA,
        )
        overlay.fill((25, 35, 20, 205))
        screen.blit(overlay, (0, 0))

        self._draw_text(
            screen,
            "GAME OVER",
            self.title_font,
            GOLD,
            (self.width // 2, 75),
        )

        self._draw_text(
            screen,
            f"Final Score: {self.score}",
            self.font,
            WHITE,
            (self.width // 2, 130),
        )

        self._draw_text(
            screen,
            "Choose a difficulty to play again",
            self.small_font,
            WHITE,
            (self.width // 2, 190),
        )

        for rect, label, action in self._menu_buttons():
            color = (
                (180, 130, 65)
                if action != "Exit"
                else (155, 75, 65)
            )

            pygame.draw.rect(
                screen,
                color,
                rect,
                border_radius=10,
            )

            pygame.draw.rect(
                screen,
                WHITE,
                rect,
                width=2,
                border_radius=10,
            )

            self._draw_text(
                screen,
                label,
                self.button_font,
                WHITE,
                rect.center,
            )

        self._draw_text(
            screen,
            "Press 1, 2, 3 to replay or 4 to exit",
            self.small_font,
            WHITE,
            (self.width // 2, self.height - 20),
        )
