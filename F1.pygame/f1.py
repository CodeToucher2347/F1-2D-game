import pygame
import math
import time

pygame.init()
pygame.mixer.init()

WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("F1: 2D Game")

WHITE = (255, 255, 255)
GREEN = (0, 200, 0)
RED = (200, 0, 0)
BLACK = (0, 0, 0)
ORANGE = (255, 165, 0)

background_start_menu = pygame.image.load("Game_wallpaper3.png")
background_start_menu = pygame.transform.scale(background_start_menu, (WIDTH, HEIGHT))

car_img = pygame.image.load("Ferrari.png")
car_img = pygame.transform.scale(car_img, (30, 50))

track_rect = pygame.Rect(100, 50, 600, 500)
inner_rect = pygame.Rect(200, 150, 400, 300)
line_x = track_rect.centerx - 5
line_y = inner_rect.top
line_height = track_rect.bottom - inner_rect.top

start_line = pygame.Rect(line_x, line_y, 10, line_height)

def generate_track_waypoints(count=100):
    waypoints = []
    cx, cy = track_rect.center
    outer_rx, outer_ry = track_rect.width / 2, track_rect.height / 2
    inner_rx, inner_ry = inner_rect.width / 2, inner_rect.height / 2
    
    mid_rx = (outer_rx + inner_rx) / 2
    mid_ry = (outer_ry + inner_ry) / 2
    
    for i in range(count):
        theta = 2 * math.pi * (1 - i / count) 
        x = cx + mid_rx * math.cos(theta)
        y = cy + mid_ry * math.sin(theta)
        waypoints.append((x, y))
    
    start_x = cx
    start_y = track_rect.bottom - 50 
    
    min_dist = float('inf')
    min_idx = 0
    for i, (x, y) in enumerate(waypoints):
        dist = (x - start_x)**2 + (y - start_y)**2
        if dist < min_dist:
            min_dist = dist
            min_idx = i
    
    waypoints = waypoints[min_idx:] + waypoints[:min_idx]
    
    return waypoints

waypoints = generate_track_waypoints(count=100)

def detect_collision(car1, car2):
    shrink_factor = 0.5
    rect1 = pygame.Rect(
        car1.x - (car1.w * shrink_factor) // 2,
        car1.y - (car1.h * shrink_factor) // 2,
        car1.w * shrink_factor,
        car1.h * shrink_factor
    )
    rect2 = pygame.Rect(
        car2.x - (car2.w * shrink_factor) // 2, 
        car2.y - (car2.h * shrink_factor) // 2,
        car2.w * shrink_factor,
        car2.h * shrink_factor
        )
    return rect1.colliderect(rect2)

class Car:
    def __init__(self):
        self.img = car_img
        self.w = self.img.get_width()
        self.h = self.img.get_height()
        self.x = WIDTH // 2
        self.y = HEIGHT - 100
        self.angle = 0
        self.speed = 0
        self.update_rotation()
        self.damage = 0
        self.last_collision_time = 0
        self.max_speed = 6
        self.collision_color_timer = 0
        self.health = 100
        self.max_health = 100
        self.default_color = (255, 255, 255)

    def update_rotation(self):
        self.rotatedSurf = pygame.transform.rotate(self.img, self.angle)
        self.rotatedRect = self.rotatedSurf.get_rect(center=(self.x, self.y))
        self.cosine = math.cos(math.radians(self.angle + 90))
        self.sine = math.sin(math.radians(self.angle + 90))
        self.head = (
            self.x + self.cosine * self.w // 2,
            self.y - self.sine * self.h // 2
        )

    def draw(self, screen):
        screen.blit(self.rotatedSurf, self.rotatedRect)
        if self.collision_color_timer > 0:
            flash_surf = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            flash_surf.fill((255, 0, 0, 100)) 
            rotated_flash = pygame.transform.rotate(flash_surf, self.angle)
            flash_rect = rotated_flash.get_rect(center=(self.x, self.y))
            screen.blit(rotated_flash, flash_rect)

    def turn_left(self):
        self.angle += 5
        self.update_rotation()

    def turn_right(self):
        self.angle -= 5
        self.update_rotation()

    def move_forward(self):
        self.speed = min(self.max_speed, 6)
        self.x += self.cosine * self.speed
        self.y -= self.sine * self.speed
        self.update_rotation()

    def move_backward(self):
        self.speed = -4
        self.x -= self.cosine * abs(self.speed)
        self.y += self.sine * abs(self.speed)
        self.update_rotation()

class AIcar:
    def __init__(self, x, y):
        self.img = pygame.transform.scale(car_img, (30, 50))
        self.w = self.img.get_width()
        self.h = self.img.get_height()
        self.x = x
        self.y = y
        self.angle = 0
        self.speed = 0
        self.max_speed = 2.5
        self.target_index = 0
        self.update_rotation()
        self.debug = True
        self.damage = 0
        self.last_collision_time = 0
        self.collision_color_timer = 0
        self.start_delay = 60
        self.forward_pressed = False
        self.left_pressed = False
        self.right_pressed = False

    def update_rotation(self):
        self.rotatedSurf = pygame.transform.rotate(self.img, self.angle)
        self.rotateRect = self.rotatedSurf.get_rect(center=(self.x, self.y))
        self.cosine = math.cos(math.radians(self.angle + 90))
        self.sine = math.sin(math.radians(self.angle + 90))
        self.head = (
            self.x + self.cosine * self.w // 2,
            self.y - self.sine * self.h // 2
        )

    def update(self):
        if len(waypoints) == 0:
            return

        if self.start_delay > 0:
            self.start_delay -= 1
            return

        target_x, target_y = waypoints[self.target_index]
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.hypot(dx, dy)

        target_angle = math.degrees(math.atan2(self.y - target_y, target_x - self.x)) - 90
        target_angle %= 360
        angle_diff = ((target_angle - self.angle) + 180) % 360 - 180

        self.forward_pressed = False
        self.left_pressed = False
        self.right_pressed = False

        if distance > 20:  
            self.forward_pressed = True  
            
            if angle_diff > 15:
                self.left_pressed = True
            elif angle_diff < -15:
                self.right_pressed = True

        if self.left_pressed:
            self.angle += 5
            self.update_rotation()
        
        if self.right_pressed:
            self.angle -= 5
            self.update_rotation()
        
        if self.forward_pressed:
            if self.speed < self.max_speed:
                self.speed += 0.1
            self.speed = min(self.speed, self.max_speed)
            
            self.x += self.cosine * self.speed
            self.y -= self.sine * self.speed
            self.update_rotation()
        else:
            self.speed = max(0, self.speed - 0.05)

        if distance < 30:
            self.target_index = (self.target_index + 1) % len(waypoints)
            print(f"AI moving to waypoint {self.target_index}")

    def draw(self, screen):
        screen.blit(self.rotatedSurf, self.rotateRect)
        
        if self.debug:
            head_x = self.x + self.cosine * 40
            head_y = self.y - self.sine * 40
            pygame.draw.line(screen, BLACK, (self.x, self.y), (head_x, head_y), 2)

class LapTimer:
    def __init__(self):
        self.start_time = time.time()
        self.laps = 0
        self.last_cross = False
        self.last_lap_time = None
        self.lap_valid = True 
        self.off_track_warning = False

    def check_crossing(self, car):
        car_rect = pygame.Rect(car.x - 15, car.y - 15, 30, 30)
        crossing = car_rect.colliderect(start_line)
        crossed = False

        if crossing and not self.last_cross and car.speed > 0:
            if self.lap_valid:
                self.laps += 1
                self.last_lap_time = time.time() - self.start_time
                print(f"Lap {self.laps} completed in {self.last_lap_time:.2f} seconds")
            else:
                print("Lap ignored: car went off track")

            self.start_time = time.time()
            self.lap_valid = True  
            crossed = True

        self.last_cross = crossing
        return crossed

    def is_on_track(self, car):
        car_point = (car.x, car.y)

        def inside_ellipse(rect, point):
            rx, ry = rect.width / 2, rect.height / 2
            cx, cy = rect.center
            px, py = point
            return ((px - cx) ** 2) / (rx ** 2) + ((py - cy) ** 2) / (ry ** 2) <= 1

        return inside_ellipse(track_rect, car_point) and not inside_ellipse(inner_rect, car_point)

    def update_lap_validity(self, car):
        if not self.is_on_track(car):
            self.lap_valid = False

    def draw(self, screen):
        font = pygame.font.SysFont(None, 24)
        lap_text = font.render(f"Laps: {self.laps}", True, BLACK)
        screen.blit(lap_text, (700, 10))

        if self.last_lap_time is not None:
            lap_time_text = font.render(f"Last Lap: {self.last_lap_time:.2f}s", True, BLACK)
        else:
            lap_time_text = font.render("Last Lap: N/A", True, BLACK)

        screen.blit(lap_time_text, (700, 30))

def draw_track():
    screen.fill(GREEN)
    pygame.draw.ellipse(screen, BLACK, track_rect)
    pygame.draw.ellipse(screen, GREEN, inner_rect)
    cx = track_rect.centerx
    top_outer = (cx, track_rect.top)
    top_inner = (cx, inner_rect.top)

    bottom_inner = (cx, inner_rect.bottom)
    bottom_outer = (cx, track_rect.bottom)
    pygame.draw.line(screen, RED, top_outer, top_inner, 4)
    pygame.draw.line(screen, RED, bottom_inner, bottom_outer, 4)

def draw_health_bar(surface, x, y, health, max_health):
    bar_width = 200
    bar_height = 20
    fill = (health / max_health) * bar_width
    border_rect = pygame.Rect(x, y, bar_width, bar_height)
    fill_rect = pygame.Rect(x, y, fill, bar_height)

    pygame.draw.rect(surface, (255, 0, 0), fill_rect)
    pygame.draw.rect(surface, (255, 255, 255), border_rect, 2)

def show_start_menu():
    pygame.mixer.music.load('f1_theme.mp3')
    pygame.mixer.music.set_volume(0.5)
    pygame.mixer.music.play(-1)
    font_title = pygame.font.SysFont(None, 72)
    font_instructions = pygame.font.SysFont(None, 36)
    title_text = font_title.render("F1: 2D Racing Game", True, WHITE)
    instruction_text = font_instructions.render("Press Enter to Start", True, WHITE)

    waiting = True
    while waiting:
        screen.blit(background_start_menu, (0, 0))
        title_x = WIDTH // 2 - title_text.get_width() // 2
        title_y = HEIGHT // 2 - 100
        instruction_x = WIDTH // 2 - instruction_text.get_width() // 2
        instruction_y = HEIGHT // 2 + 20
        screen.blit(title_text, (title_x, title_y))
        screen.blit(instruction_text, (instruction_x, instruction_y))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    pygame.mixer.music.stop()
                    waiting = False
                    return
        pygame.display.flip()

def main():
    clock = pygame.time.Clock()
    car = Car()
    
    global waypoints
    waypoints = generate_track_waypoints(count=100)
    
    start_point = waypoints[0]
    next_point = waypoints[1]
    ai_car = AIcar(*start_point)

    dx = next_point[0] - start_point[0]
    dy = next_point[1] - start_point[1]
    ai_car.angle = (math.degrees(math.atan2(-dy, dx)) + 90) % 360
    ai_car.update_rotation()
    
    player_spawn_point = waypoints[98]
    car.x = player_spawn_point[0]
    car.y = player_spawn_point[1]
    player_next_point = waypoints[99]
    player_dx = player_next_point[0] - player_spawn_point[0]
    player_dy = player_next_point[1] - player_spawn_point[1]
    car.angle = (math.degrees(math.atan2(-player_dy, player_dx)) + 90) % 360
    car.update_rotation()
    
    timer = LapTimer()
    game_pause = False
    font = pygame.font.SysFont(None, 48)
    
    ai_car.debug = False
    
    running = True
    while running:
        clock.tick(60)
        screen.fill(GREEN)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    game_pause = not game_pause
                elif event.key == pygame.K_d:
                    ai_car.debug = not ai_car.debug
                elif event.key == pygame.K_r:
                    ai_car = AIcar(*waypoints[0])
                elif event.key == pygame.K_n:
                    ai_car.target_index = (ai_car.target_index + 1) % len(waypoints)
                elif event.key == pygame.K_s:
                    ai_car.max_speed += 0.5
                    print(f"AI max speed: {ai_car.max_speed}")
                elif event.key == pygame.K_a:
                    ai_car.max_speed = max(0.5, ai_car.max_speed - 0.5)
                    print(f"AI max speed: {ai_car.max_speed}")
        
        if detect_collision(car, ai_car):
            now = time.time()
            car.collision_color_timer = 15
            ai_car.collision_color_timer = 15
            if now - car.last_collision_time > 1:
                car.damage += 10
                ai_car.damage += 10
                car.health -= 20
                car.speed = max(0,car.speed - 2)
                ai_car.speed = max(0, ai_car.speed - 1)
                car.max_speed = max(3, car.max_speed - 0.5)
                ai_car.max_speed = max(0.5, ai_car.max_speed - 0.5)
                car.last_collision_time = now
                ai_car.last_collision_time = now
        
        if car.collision_color_timer > 0:
            car.collision_color_timer -= 1
        if ai_car.collision_color_timer > 0:
            ai_car.collision_color_timer -=1

        if not game_pause:
            keys = pygame.key.get_pressed()
            ai_car.update()
            car.speed = 0

            if keys[pygame.K_LEFT]:
                car.turn_left()
            if keys[pygame.K_RIGHT]:
                car.turn_right()
            if keys[pygame.K_UP]:
                car.move_forward()
            if keys[pygame.K_DOWN]:
                car.move_backward()

            timer.update_lap_validity(car)
            timer.check_crossing(car)

        draw_track()
        car.draw(screen)
        ai_car.draw(screen)
        timer.draw(screen)  
        draw_health_bar(screen, 20, 20, car.health, car.max_health)

        if ai_car.debug:
            wp_text = font.render(f"WP: {ai_car.target_index}", True, BLACK)
            screen.blit(wp_text, (10, HEIGHT - 40))

        if game_pause:
            pause_text = font.render("PAUSED", True, RED)
            screen.blit(pause_text, (WIDTH // 2 - 80, HEIGHT // 2))

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    show_start_menu()
    try:
        main()
    except Exception as e:
        print("ERROR",e)
        pygame.quit()