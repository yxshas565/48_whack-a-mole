import pygame

from game.game_engine import GameEngine


WIDTH, HEIGHT = 500, 560
FPS = 60

pygame.init()

SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Whack-a-Mole - Pygame Version")

clock = pygame.time.Clock()
engine = GameEngine(WIDTH, HEIGHT)


def main():
    running = True

    while running:
        for event in pygame.event.get():
            engine.handle_event(event)

        if engine.state == "exit":
            running = False
            continue

        engine.handle_input()
        engine.update()
        engine.render(SCREEN)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
