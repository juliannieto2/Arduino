"""
Interactive Automated Warehouse Picking Simulator with Pygame.
"""

import sys
import os
import math
import time
import pygame
from typing import List, Tuple, Dict, Optional

from warehouse_model import WarehouseModel, AISLES, LEVELS

# Pygame Initialization
pygame.init()
pygame.font.init()

# Color Palette
BG_COLOR = (245, 247, 250)
PANEL_BG = (255, 255, 255)
DARK_TEXT = (44, 62, 80)
LIGHT_TEXT = (236, 240, 241)
ACCENT_BLUE = (52, 152, 219)
ACCENT_GREEN = (46, 204, 113)
ACCENT_RED = (231, 76, 60)
ACCENT_ORANGE = (230, 126, 34)
CORRIDOR_COLOR = (220, 224, 230)
RACK_BORDER = (127, 140, 141)
TERMINAL_BG = (20, 24, 30)
TERMINAL_TEXT = (46, 204, 113)

# Fonts
FONT_TITLE = pygame.font.SysFont("Arial", 18, bold=True)
FONT_LABEL = pygame.font.SysFont("Arial", 14, bold=True)
FONT_SMALL = pygame.font.SysFont("Arial", 11)
FONT_TERM = pygame.font.SysFont("Consolas", 12)

# Screen Dimensions
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 750

class UIElement:
    pass

class Button:
    def __init__(self, x: int, y: int, w: int, h: int, text: str, bg_color=ACCENT_BLUE, text_color=(255, 255, 255)):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.bg_color = bg_color
        self.text_color = text_color
        self.is_hovered = False

    def draw(self, surface: pygame.Surface):
        color = (min(self.bg_color[0]+20, 255), min(self.bg_color[1]+20, 255), min(self.bg_color[2]+20, 255)) if self.is_hovered else self.bg_color
        pygame.draw.rect(surface, color, self.rect, border_radius=6)
        pygame.draw.rect(surface, (100, 100, 100), self.rect, width=1, border_radius=6)
        txt = FONT_LABEL.render(self.text, True, self.text_color)
        txt_rect = txt.get_rect(center=self.rect.center)
        surface.blit(txt, txt_rect)

    def check_hover(self, pos: Tuple[int, int]):
        self.is_hovered = self.rect.collidepoint(pos)

    def is_clicked(self, pos: Tuple[int, int], click: bool) -> bool:
        return click and self.rect.collidepoint(pos)


class WarehouseSimulator:
    def __init__(self, headless=False):
        self.headless = headless
        if headless:
            os.environ['SDL_VIDEODRIVER'] = 'dummy'

        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Simulador de Control y Picking - Almacén Automatizado")
        self.clock = pygame.time.Clock()

        self.wm = WarehouseModel()

        # Selection state
        self.selected_sud = 14
        self.selected_level = 2
        self.target_sud = None
        self.target_level = None

        # Robot State Machine
        # States: IDLE, MOVING_TO_AISLE, MOVING_IN_AISLE, ELEVATING, PICKING, LOWERING, RETURNING_AISLE, RETURNING_CORRIDOR
        self.robot_state = "IDLE"
        self.robot_speed = 4.0
        self.actuator_level = 1.0  # 1.0 (Nivel 1) to 2.0 (Nivel 2)
        self.actuator_target = 1.0
        self.actuator_speed = 0.04
        self.state_timer = 0

        # Serial Monitor Logs
        self.serial_logs: List[str] = [
            "[ARDUINO] Sistema de Control de Almacén Inicializado.",
            "[ARDUINO] Esperando comando de picking..."
        ]

        # Geometry setup
        self.setup_geometry()
        self.setup_ui()

    def setup_geometry(self):
        # Canvas dimensions: 750 x 710 on left
        self.map_rect = pygame.Rect(15, 15, 750, 720)

        # Main corridor at bottom: y = 600 to 670
        self.main_corridor_y = 635
        self.salida_x = 75
        self.salida_y = self.main_corridor_y

        # Robot initial position
        self.robot_x = float(self.salida_x)
        self.robot_y = float(self.salida_y)

        # Aisles x positions
        self.aisle_x = {
            "Pasillo A": 160,
            "Pasillo B": 280,
            "Pasillo C": 400,
            "Pasillo D": 520,
            "Pasillo E": 640
        }

        # Satellite positions calculations (Sud 1 to 63)
        # Depth index 1 is closest to main corridor (bottom, y ~ 560)
        # Depth index 9 is furthest top (y ~ 80)
        self.sud_rects: Dict[int, pygame.Rect] = {}
        self.sud_coords: Dict[int, Tuple[int, int]] = {}  # robot stop coords in front of Sud

        slot_w = 40
        slot_h = 45

        for sud_id in range(1, 64):
            info = self.wm.get_location_info(sud_id)
            aisle = info["aisle"]
            side = info["side"]
            depth = info["depth_index"]

            ax = self.aisle_x[aisle]
            # y coordinate: depth 1 -> bottom y=540, depth 9 -> top y=80
            y_pos = 540 - (depth - 1) * 55

            if side == "left":
                rx = ax - slot_w - 5
            else:  # right
                rx = ax + 5

            rect = pygame.Rect(rx, y_pos, slot_w, slot_h)
            self.sud_rects[sud_id] = rect

            # Stop coord in aisle in front of this rack position
            self.sud_coords[sud_id] = (ax, y_pos + slot_h // 2)

    def setup_ui(self):
        # UI controls on right panel (x = 780 to 1180)
        px = 785

        self.btn_sud_dec = Button(px, 140, 45, 35, "-1", ACCENT_BLUE)
        self.btn_sud_inc = Button(px + 175, 140, 45, 35, "+1", ACCENT_BLUE)
        self.btn_sud_quick14 = Button(px + 230, 140, 75, 35, "Sud 14", ACCENT_ORANGE)
        self.btn_sud_quick32 = Button(px + 310, 140, 75, 35, "Sud 32", ACCENT_ORANGE)

        self.btn_lvl1 = Button(px, 220, 180, 35, "Nivel 01 (Base)", ACCENT_BLUE)
        self.btn_lvl2 = Button(px + 190, 220, 185, 35, "Nivel 02 (Elevado)", ACCENT_BLUE)

        self.btn_start = Button(px, 280, 375, 45, "► INICIAR PICKING AUTOMÁTICO", ACCENT_GREEN)
        self.btn_return = Button(px, 335, 180, 35, "↩ Ir a SALIDA", ACCENT_BLUE)
        self.btn_random = Button(px + 190, 335, 185, 35, "🎲 Pedido Aleatorio", ACCENT_ORANGE)

    def add_log(self, text: str):
        self.serial_logs.append(text)
        if len(self.serial_logs) > 16:
            self.serial_logs.pop(0)

    def start_picking(self):
        if self.robot_state != "IDLE":
            return

        self.target_sud = self.selected_sud
        self.target_level = self.selected_level
        info = self.wm.get_location_info(self.target_sud)
        aisle = info["aisle"]

        self.add_log(f"[ARDUINO] NAVEGACIÓN: Iniciando ciclo hacia Sud {self.target_sud} ({aisle}) - Level {self.target_level}")
        self.robot_state = "MOVING_TO_AISLE"

    def update_robot(self):
        if self.robot_state == "IDLE":
            return

        info = self.wm.get_location_info(self.target_sud) if self.target_sud else None
        target_aisle_x = self.aisle_x[info["aisle"]] if info else self.salida_x
        target_sud_x, target_sud_y = self.sud_coords[self.target_sud] if self.target_sud else (self.salida_x, self.salida_y)

        if self.robot_state == "MOVING_TO_AISLE":
            # Move along main corridor y=main_corridor_y to target_aisle_x
            dx = target_aisle_x - self.robot_x
            if abs(dx) <= self.robot_speed:
                self.robot_x = target_aisle_x
                self.robot_state = "MOVING_IN_AISLE"
                self.add_log(f"[ARDUINO] GIRANDO: Entrando a {info['aisle']}...")
            else:
                self.robot_x += math.copysign(self.robot_speed, dx)

        elif self.robot_state == "MOVING_IN_AISLE":
            # Move along aisle x=target_aisle_x to target_sud_y
            dy = target_sud_y - self.robot_y
            if abs(dy) <= self.robot_speed:
                self.robot_y = target_sud_y
                self.robot_state = "ELEVATING"
                self.actuator_target = float(self.target_level)
                self.add_log(f"[ARDUINO] POSICIONADO en Sud {self.target_sud}. Elevando actuador a Nivel {self.target_level:02d}...")
            else:
                self.robot_y += math.copysign(self.robot_speed, dy)

        elif self.robot_state == "ELEVATING":
            # Elevate actuator to target level
            if abs(self.actuator_level - self.actuator_target) <= self.actuator_speed:
                self.actuator_level = self.actuator_target
                self.robot_state = "PICKING"
                self.state_timer = 40  # 40 frames delay for picking animation
                self.add_log(f"[ARDUINO] ACTUADOR EN NIVEL {self.target_level:02d}. Ejecutando extracción de pieza...")
            else:
                self.actuator_level += math.copysign(self.actuator_speed, self.actuator_target - self.actuator_level)

        elif self.robot_state == "PICKING":
            self.state_timer -= 1
            if self.state_timer <= 0:
                self.robot_state = "LOWERING"
                self.actuator_target = 1.0
                self.add_log(f"[ARDUINO] PIEZA EXTRAÍDA. Replegando actuador vertical a Nivel 01...")

        elif self.robot_state == "LOWERING":
            if abs(self.actuator_level - self.actuator_target) <= self.actuator_speed:
                self.actuator_level = 1.0
                self.robot_state = "RETURNING_AISLE"
                self.add_log(f"[ARDUINO] RETORNO: Iniciando movimiento de salida de pasillo...")
            else:
                self.actuator_level += math.copysign(self.actuator_speed, self.actuator_target - self.actuator_level)

        elif self.robot_state == "RETURNING_AISLE":
            # Return down aisle to main corridor y=main_corridor_y
            dy = self.main_corridor_y - self.robot_y
            if abs(dy) <= self.robot_speed:
                self.robot_y = self.main_corridor_y
                self.robot_state = "RETURNING_CORRIDOR"
                self.add_log(f"[ARDUINO] Retornando por pasillo principal hacia SALIDA...")
            else:
                self.robot_y += math.copysign(self.robot_speed, dy)

        elif self.robot_state == "RETURNING_CORRIDOR":
            # Return along main corridor to salida_x
            dx = self.salida_x - self.robot_x
            if abs(dx) <= self.robot_speed:
                self.robot_x = self.salida_x
                self.robot_state = "IDLE"
                self.add_log(f"[ARDUINO] LLEGADA A SALIDA: Pedido Sud {self.target_sud} completado. Robot en REPOSO.")
            else:
                self.robot_x += math.copysign(self.robot_speed, dx)

    def draw_map(self):
        # Background canvas for map
        pygame.draw.rect(self.screen, PANEL_BG, self.map_rect, border_radius=10)
        pygame.draw.rect(self.screen, (210, 215, 225), self.map_rect, width=2, border_radius=10)

        # Title map
        title = FONT_TITLE.render("PLANO ESQUEMÁTICO DEL ALMACÉN DE PICKING (2D)", True, DARK_TEXT)
        self.screen.blit(title, (30, 25))

        # Main corridor path (bottom)
        corridor_rect = pygame.Rect(self.map_rect.left + 20, self.main_corridor_y - 20, self.map_rect.width - 40, 40)
        pygame.draw.rect(self.screen, CORRIDOR_COLOR, corridor_rect, border_radius=6)

        # Aisle paths (vertical)
        for aisle_name, ax in self.aisle_x.items():
            path_rect = pygame.Rect(ax - 18, 60, 36, self.main_corridor_y - 40)
            pygame.draw.rect(self.screen, CORRIDOR_COLOR, path_rect)
            # Aisle label top
            lbl = FONT_LABEL.render(aisle_name, True, DARK_TEXT)
            lbl_rect = lbl.get_rect(center=(ax, 48))
            self.screen.blit(lbl, lbl_rect)

        # SALIDA Zone
        salida_rect = pygame.Rect(self.salida_x - 35, self.main_corridor_y - 35, 70, 70)
        pygame.draw.rect(self.screen, (46, 204, 113), salida_rect, border_radius=8)
        pygame.draw.rect(self.screen, (39, 174, 96), salida_rect, width=3, border_radius=8)
        s_txt1 = FONT_LABEL.render("ZONA DE", True, (255, 255, 255))
        s_txt2 = FONT_LABEL.render("SALIDA", True, (255, 255, 255))
        self.screen.blit(s_txt1, s_txt1.get_rect(center=(self.salida_x, self.main_corridor_y - 10)))
        self.screen.blit(s_txt2, s_txt2.get_rect(center=(self.salida_x, self.main_corridor_y + 10)))

        # Draw Satellite Racks (Sud 1 to Sud 63)
        for sud_id in range(1, 64):
            rect = self.sud_rects[sud_id]
            is_selected = (sud_id == self.selected_sud)
            is_target = (sud_id == self.target_sud)

            # Color from heat map
            color = self.wm.get_popularity_color(sud_id)

            # Fill
            pygame.draw.rect(self.screen, color, rect, border_radius=4)

            # Selection / Target border highlight
            if is_target:
                pygame.draw.rect(self.screen, ACCENT_RED, rect, width=3, border_radius=4)
            elif is_selected:
                pygame.draw.rect(self.screen, (41, 128, 185), rect, width=3, border_radius=4)
            else:
                pygame.draw.rect(self.screen, RACK_BORDER, rect, width=1, border_radius=4)

            # Label text inside grid cell
            txt_num = FONT_SMALL.render(f"S{sud_id}", True, (20, 20, 20))
            self.screen.blit(txt_num, txt_num.get_rect(center=rect.center))

        # Popularity Legend at bottom
        leg_y = 690
        lbl_leg = FONT_SMALL.render("Mapa de Calor (Popularidad/Rotación):", True, DARK_TEXT)
        self.screen.blit(lbl_leg, (30, leg_y))

        swatches = [
            ("Alta (Cerca Salida)", (46, 204, 113)),
            ("Media-Alta", (241, 196, 15)),
            ("Media-Baja", (230, 126, 34)),
            ("Baja (Fondo)", (180, 100, 100))
        ]
        lx = 240
        for name, col in swatches:
            pygame.draw.rect(self.screen, col, (lx, leg_y, 15, 15), border_radius=3)
            txt_sw = FONT_SMALL.render(name, True, DARK_TEXT)
            self.screen.blit(txt_sw, (lx + 20, leg_y))
            lx += 130

        # Draw Robot
        self.draw_robot()

    def draw_robot(self):
        rx, ry = int(self.robot_x), int(self.robot_y)

        # Robot Chassis
        rw, rh = 32, 32
        chassis_rect = pygame.Rect(rx - rw//2, ry - rh//2, rw, rh)

        # Color based on state
        chassis_color = (231, 76, 60) if self.robot_state == "PICKING" else (52, 152, 219)
        pygame.draw.rect(self.screen, chassis_color, chassis_rect, border_radius=6)
        pygame.draw.rect(self.screen, (24, 44, 97), chassis_rect, width=2, border_radius=6)

        # Robot wheels
        pygame.draw.rect(self.screen, (40, 40, 40), (rx - rw//2 - 3, ry - 12, 4, 8))
        pygame.draw.rect(self.screen, (40, 40, 40), (rx + rw//2 - 1, ry - 12, 4, 8))
        pygame.draw.rect(self.screen, (40, 40, 40), (rx - rw//2 - 3, ry + 4, 4, 8))
        pygame.draw.rect(self.screen, (40, 40, 40), (rx + rw//2 - 1, ry + 4, 4, 8))

        # Actuator Level Visualizer (vertical mast elevation indicator)
        # Mast height grows when level increases to 2
        mast_height = int(10 * self.actuator_level)
        pygame.draw.rect(self.screen, (241, 196, 15), (rx - 4, ry - mast_height - 2, 8, mast_height), border_radius=2)

        # Level indicator badge
        lvl_str = f"L{int(round(self.actuator_level))}"
        txt_lvl = FONT_SMALL.render(lvl_str, True, (255, 255, 255))
        self.screen.blit(txt_lvl, txt_lvl.get_rect(center=(rx, ry)))

    def draw_control_panel(self):
        panel_rect = pygame.Rect(775, 15, 410, 720)
        pygame.draw.rect(self.screen, PANEL_BG, panel_rect, border_radius=10)
        pygame.draw.rect(self.screen, (210, 215, 225), panel_rect, width=2, border_radius=10)

        px = 785
        # Title
        title = FONT_TITLE.render("PANEL DE CONTROL DE PICKING", True, DARK_TEXT)
        self.screen.blit(title, (px, 25))

        # Destination Selection Section
        lbl_sec1 = FONT_LABEL.render("1. SELECCIÓN DE UBICACIÓN (SUD 1 - 63):", True, DARK_TEXT)
        self.screen.blit(lbl_sec1, (px, 65))

        # Big Display for Selected Sud
        info = self.wm.get_location_info(self.selected_sud)
        sud_display_rect = pygame.Rect(px + 55, 95, 110, 35)
        pygame.draw.rect(self.screen, (235, 240, 245), sud_display_rect, border_radius=6)
        pygame.draw.rect(self.screen, (180, 190, 200), sud_display_rect, width=1, border_radius=6)

        display_txt = FONT_TITLE.render(f"Sud {self.selected_sud}", True, ACCENT_BLUE)
        self.screen.blit(display_txt, display_txt.get_rect(center=sud_display_rect.center))

        info_txt = FONT_SMALL.render(f"({info['aisle']}, Lado {info['side'].capitalize()}, Prof: {info['depth_index']})", True, DARK_TEXT)
        self.screen.blit(info_txt, (px + 175, 105))

        # Draw Buttons
        self.btn_sud_dec.draw(self.screen)
        self.btn_sud_inc.draw(self.screen)
        self.btn_sud_quick14.draw(self.screen)
        self.btn_sud_quick32.draw(self.screen)

        # Level Selection Section
        lbl_sec2 = FONT_LABEL.render("2. SELECCIÓN DE NIVEL VERTICAL:", True, DARK_TEXT)
        self.screen.blit(lbl_sec2, (px, 190))

        # Highlight active level button
        if self.selected_level == 1:
            self.btn_lvl1.bg_color = (39, 174, 96)
            self.btn_lvl2.bg_color = (149, 165, 166)
        else:
            self.btn_lvl1.bg_color = (149, 165, 166)
            self.btn_lvl2.bg_color = (39, 174, 96)

        self.btn_lvl1.draw(self.screen)
        self.btn_lvl2.draw(self.screen)

        # Action Buttons
        self.btn_start.draw(self.screen)
        self.btn_return.draw(self.screen)
        self.btn_random.draw(self.screen)

        # Divider
        pygame.draw.line(self.screen, (220, 225, 230), (px, 385), (px + 390, 385), 2)

        # Serial Monitor Section
        lbl_sec3 = FONT_LABEL.render("MONITOR SERIAL ARDUINO (SIMULADO)", True, DARK_TEXT)
        self.screen.blit(lbl_sec3, (px, 395))

        term_rect = pygame.Rect(px, 420, 390, 300)
        pygame.draw.rect(self.screen, TERMINAL_BG, term_rect, border_radius=6)
        pygame.draw.rect(self.screen, (50, 60, 70), term_rect, width=1, border_radius=6)

        # Print logs inside terminal
        ty = 428
        for log in self.serial_logs[-15:]:
            txt_log = FONT_TERM.render(log, True, TERMINAL_TEXT)
            self.screen.blit(txt_log, (px + 10, ty))
            ty += 19

    def handle_events(self):
        mouse_pos = pygame.mouse.get_pos()
        click = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                click = True

        # Check hover
        for btn in [self.btn_sud_dec, self.btn_sud_inc, self.btn_sud_quick14, self.btn_sud_quick32,
                    self.btn_lvl1, self.btn_lvl2, self.btn_start, self.btn_return, self.btn_random]:
            btn.check_hover(mouse_pos)

        # Handle clicks on map racks to select Sud directly
        if click and self.map_rect.collidepoint(mouse_pos):
            for sud_id, rect in self.sud_rects.items():
                if rect.collidepoint(mouse_pos):
                    self.selected_sud = sud_id
                    break

        # Handle button clicks
        if self.btn_sud_dec.is_clicked(mouse_pos, click):
            self.selected_sud = max(1, self.selected_sud - 1)
        if self.btn_sud_inc.is_clicked(mouse_pos, click):
            self.selected_sud = min(63, self.selected_sud + 1)
        if self.btn_sud_quick14.is_clicked(mouse_pos, click):
            self.selected_sud = 14
            self.selected_level = 2
        if self.btn_sud_quick32.is_clicked(mouse_pos, click):
            self.selected_sud = 32
            self.selected_level = 1
        if self.btn_lvl1.is_clicked(mouse_pos, click):
            self.selected_level = 1
        if self.btn_lvl2.is_clicked(mouse_pos, click):
            self.selected_level = 2
        if self.btn_start.is_clicked(mouse_pos, click):
            self.start_picking()
        if self.btn_random.is_clicked(mouse_pos, click):
            import random
            self.selected_sud = random.randint(1, 63)
            self.selected_level = random.choice([1, 2])
            self.start_picking()
        if self.btn_return.is_clicked(mouse_pos, click):
            self.target_sud = None
            self.robot_state = "RETURNING_CORRIDOR"

        return True

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.update_robot()

            self.screen.fill(BG_COLOR)
            self.draw_map()
            self.draw_control_panel()

            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()

    def run_headless_simulation(self, output_image_path: str = "warehouse_sim.png"):
        """
        Runs headless simulation steps and saves screenshot verification image.
        """
        self.selected_sud = 14
        self.selected_level = 2
        self.start_picking()

        # Run several frames to animate robot moving into aisle B and picking
        for step in range(250):
            self.update_robot()
            self.screen.fill(BG_COLOR)
            self.draw_map()
            self.draw_control_panel()

        pygame.image.save(self.screen, output_image_path)
        print(f"Headless simulation rendered and screenshot saved to {output_image_path}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--headless":
        sim = WarehouseSimulator(headless=True)
        sim.run_headless_simulation("warehouse_sim_screenshot.png")
    else:
        sim = WarehouseSimulator(headless=False)
        sim.run()
