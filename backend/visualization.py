"""
Pygame Real-Time Elevator Fleet Visualizer.

Renders a live 2D cross-section of the building showing:
    - Numbered floor labels
    - Elevator shafts with car position, direction arrow, passenger count
    - Color-coded states: GREEN=IDLE, BLUE=UP, RED=DOWN, GREY=NON-OPERATIONAL
    - Waiting passengers at origin floors (yellow dots)
    - On-board passengers inside elevator cars (white dots)
    - Live stats overlay: step, avg wait, SLA, calls, completed
    - Pending call indicators on floors

Controls:
    SPACE  — pause / resume
    UP     — increase sim speed
    DOWN   — decrease sim speed
    ESC    — quit

Usage:
    python -m backend.main --visualize
"""

from __future__ import annotations

import sys
import os
from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from backend.simulator.engine import SimulationEngine

# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------
BLACK       = (15, 15, 25)
DARK_BG     = (25, 25, 40)
PANEL_BG    = (30, 32, 48)
FLOOR_LINE  = (50, 55, 75)
FLOOR_TEXT  = (140, 150, 175)
SHAFT_BG    = (38, 40, 58)
SHAFT_BORDER= (60, 65, 90)

# Elevator car colors by state
COLOR_IDLE  = (46, 204, 113)    # Green
COLOR_UP    = (52, 152, 219)    # Blue
COLOR_DOWN  = (231, 76, 60)     # Red
COLOR_OFF   = (100, 100, 110)   # Grey (non-operational)

# Passenger / call colors
PAX_WAITING = (241, 196, 15)    # Yellow
PAX_ONBOARD = (236, 240, 241)   # White
CALL_UP     = (46, 204, 113)    # Green arrow
CALL_DOWN   = (231, 76, 60)     # Red arrow

# UI
TEXT_WHITE  = (220, 225, 235)
TEXT_DIM    = (120, 130, 150)
ACCENT      = (100, 140, 255)
SLA_OK      = (46, 204, 113)
SLA_WARN    = (241, 196, 15)
SLA_FAIL    = (231, 76, 60)
HEADER_BG   = (20, 22, 35)
SPEED_BAR   = (80, 100, 200)


# ---------------------------------------------------------------------------
# Visualizer
# ---------------------------------------------------------------------------
class ElevatorVisualizer:
    """Pygame-based real-time elevator fleet visualizer."""

    # Layout constants
    LEFT_MARGIN = 70          # Floor labels
    RIGHT_PANEL_W = 280       # Stats panel
    SHAFT_GAP = 12            # Gap between shafts
    TOP_MARGIN = 60           # Header
    BOTTOM_MARGIN = 40        # Footer
    CAR_WIDTH = 64
    CAR_HEIGHT = 28
    MIN_FLOOR_H = 36

    def __init__(self, simulator: "SimulationEngine") -> None:
        self.sim = simulator
        self.num_floors = simulator.building.num_floors
        self.num_elevators = len(simulator.building.elevators)

        # Calculate window size
        shaft_area_w = (
            self.num_elevators * (self.CAR_WIDTH + self.SHAFT_GAP)
            + self.SHAFT_GAP
        )
        self.win_w = self.LEFT_MARGIN + shaft_area_w + self.RIGHT_PANEL_W + 20
        self.win_w = max(self.win_w, 700)

        floor_h = max(self.MIN_FLOOR_H, 500 // self.num_floors)
        self.floor_h = floor_h
        self.win_h = (
            self.TOP_MARGIN
            + self.num_floors * floor_h
            + self.BOTTOM_MARGIN
        )
        self.win_h = max(self.win_h, 500)
        self.win_h = min(self.win_h, 900)
        # Recalculate floor_h if clamped
        available = self.win_h - self.TOP_MARGIN - self.BOTTOM_MARGIN
        self.floor_h = available // self.num_floors

        # Shaft area origin
        self.shaft_x0 = self.LEFT_MARGIN
        self.shaft_area_w = shaft_area_w

        # Sim speed
        self.speed = 0.1
        self.frame_accumulator = 0.0
        self.max_speed = 20.0
        self.paused = False
        self.running = True
        self.floor_buttons = {}  # type: dict[int, pygame.Rect]
        self.selected_origin_floor = None
        self.pending_passenger_count = 0
        self.selected_dest_floor = None
        self.scenario_case = self.sim.config["simulation"].get("scenario_case", 1)

    # ------------------------------------------------------------------
    # Coordinate helpers
    # ------------------------------------------------------------------
    def _floor_y(self, floor: int) -> int:
        """Return the top-Y pixel for a given floor (floor 1 = bottom)."""
        # Floor 1 is at the bottom, floor N at the top
        return self.TOP_MARGIN + (self.num_floors - floor) * self.floor_h

    def _shaft_x(self, elevator_idx: int) -> int:
        """Return the left-X pixel for a given elevator shaft."""
        return (
            self.shaft_x0
            + self.SHAFT_GAP
            + elevator_idx * (self.CAR_WIDTH + self.SHAFT_GAP)
        )

    def _get_clicked_elevator(self, pos: tuple[int, int]) -> int | None:
        """Return the elevator index if pos is inside an elevator shaft."""
        x, y = pos
        building_top = self.TOP_MARGIN
        building_bottom = self.TOP_MARGIN + self.num_floors * self.floor_h
        if building_top <= y <= building_bottom:
            for i in range(self.num_elevators):
                sx = self._shaft_x(i)
                if sx <= x <= sx + self.CAR_WIDTH:
                    return i
        return None

    # ------------------------------------------------------------------
    # Drawing helpers
    # ------------------------------------------------------------------
    def _draw_building(self, screen: pygame.Surface) -> None:
        """Draw the building frame, floor lines, and labels."""
        building_x = self.shaft_x0
        building_w = self.shaft_area_w
        building_top = self.TOP_MARGIN
        building_bottom = self.TOP_MARGIN + self.num_floors * self.floor_h

        # Building background
        pygame.draw.rect(
            screen, DARK_BG,
            (building_x, building_top, building_w, building_bottom - building_top),
        )

        # Floor lines and labels
        font_sm = pygame.font.SysFont("Consolas", 13)
        for f in range(1, self.num_floors + 1):
            y = self._floor_y(f)
            # Floor line
            pygame.draw.line(
                screen, FLOOR_LINE,
                (building_x, y + self.floor_h),
                (building_x + building_w, y + self.floor_h),
            )
            # Floor label
            label = font_sm.render(f"F{f:>2}", True, FLOOR_TEXT)
            screen.blit(label, (building_x - 38, y + self.floor_h // 2 - 7))

            # Add passenger button
            btn_rect = pygame.Rect(building_x - 62, y + self.floor_h // 2 - 8, 16, 16)
            self.floor_buttons[f] = btn_rect
            is_selected_origin = getattr(self, "selected_origin_floor", None) == f
            is_selected_dest = getattr(self, "selected_dest_floor", None) == f
            btn_color = (255, 100, 100) if is_selected_origin else ((241, 196, 15) if is_selected_dest else ACCENT)
            pygame.draw.rect(screen, btn_color, btn_rect, border_radius=3)
            plus = font_sm.render("+", True, BLACK)
            screen.blit(plus, (btn_rect.x + 4, btn_rect.y + 1))

            if is_selected_origin and getattr(self, "pending_passenger_count", 0) > 0:
                count_str = str(self.pending_passenger_count)
                count_surf = font_sm.render(count_str, True, (255, 255, 255))
                pygame.draw.circle(screen, (200, 50, 50), (btn_rect.x - 10, btn_rect.y + 8), 8)
                screen.blit(count_surf, (btn_rect.x - 10 - count_surf.get_width() // 2, btn_rect.y + 8 - count_surf.get_height() // 2))

        # Building border
        pygame.draw.rect(
            screen, SHAFT_BORDER,
            (building_x, building_top, building_w, building_bottom - building_top),
            2,
        )

        # Shaft separators
        for i in range(self.num_elevators):
            sx = self._shaft_x(i)
            pygame.draw.rect(
                screen, SHAFT_BG,
                (sx - 2, building_top, self.CAR_WIDTH + 4, building_bottom - building_top),
            )

    def _draw_elevators(self, screen: pygame.Surface) -> None:
        """Draw each elevator car at its current floor."""
        font = pygame.font.SysFont("Consolas", 12, bold=True)
        font_sm = pygame.font.SysFont("Consolas", 10)

        for elev in self.sim.building.elevators:
            eid = elev.elevator_id
            sx = self._shaft_x(eid)
            cy = self._floor_y(elev.current_floor) + (self.floor_h - self.CAR_HEIGHT) // 2

            # Color by state
            if not elev.is_operational:
                color = COLOR_OFF
            elif elev.direction == "UP":
                color = COLOR_UP
            elif elev.direction == "DOWN":
                color = COLOR_DOWN
            else:
                color = COLOR_IDLE

            # Draw car body
            car_rect = pygame.Rect(sx, cy, self.CAR_WIDTH, self.CAR_HEIGHT)
            pygame.draw.rect(screen, color, car_rect, border_radius=4)
            pygame.draw.rect(screen, TEXT_WHITE, car_rect, 1, border_radius=4)

            # Direction arrow
            arrow = ""
            if elev.direction == "UP":
                arrow = "^"
            elif elev.direction == "DOWN":
                arrow = "v"

            # Elevator ID + passenger count + arrow
            pax_count = len(elev.passengers)
            label = f"E{eid}{arrow} {pax_count}p"
            text_surf = font.render(label, True, BLACK)
            text_rect = text_surf.get_rect(center=car_rect.center)
            screen.blit(text_surf, text_rect)

            # Occupancy bar below car
            bar_y = cy + self.CAR_HEIGHT + 2
            bar_w = self.CAR_WIDTH
            bar_h = 4
            pct = elev.occupancy_percent() / 100.0
            pygame.draw.rect(screen, SHAFT_BORDER, (sx, bar_y, bar_w, bar_h))
            fill_color = SLA_OK if pct < 0.7 else (SLA_WARN if pct < 0.9 else SLA_FAIL)
            pygame.draw.rect(
                screen, fill_color,
                (sx, bar_y, int(bar_w * min(pct, 1.0)), bar_h),
            )

            # Shaft header (elevator label at top)
            hdr = font_sm.render(f"E{eid}", True, TEXT_DIM)
            screen.blit(hdr, (sx + self.CAR_WIDTH // 2 - hdr.get_width() // 2, self.TOP_MARGIN - 16))

    def _draw_passengers(self, screen: pygame.Surface) -> None:
        """Draw waiting passengers as dots at their origin floor."""
        for cid, rec in self.sim._active_passengers.items():
            if rec["state"] == "WAITING":
                pax = rec["passenger"]
                floor = pax.origin_floor
                eid = rec["elevator_id"]
                # Draw yellow dot at the floor, near the assigned elevator shaft
                sx = self._shaft_x(eid)
                fy = self._floor_y(floor) + self.floor_h // 2
                pygame.draw.circle(screen, PAX_WAITING, (sx - 6, fy), 4)

    def _draw_pending_calls(self, screen: pygame.Surface) -> None:
        """Draw small call indicators on the left side of the building."""
        building_x = self.shaft_x0
        font_sm = pygame.font.SysFont("Consolas", 10)

        # Count calls per floor
        floor_calls: dict[int, list[str]] = {}
        for f, _ts in self.sim.building.up_calls:
            floor_calls.setdefault(f, []).append("U")
        for f, _ts in self.sim.building.down_calls:
            floor_calls.setdefault(f, []).append("D")
        for f, _ts in self.sim.building.express_calls:
            floor_calls.setdefault(f, []).append("X")

        for floor, dirs in floor_calls.items():
            fy = self._floor_y(floor) + self.floor_h // 2
            for i, d in enumerate(dirs[:3]):
                color = CALL_UP if d == "U" else (SLA_FAIL if d == "X" else CALL_DOWN)
                marker = font_sm.render(d, True, color)
                screen.blit(marker, (building_x + 4 + i * 10, fy - 5))

    def _draw_header(self, screen: pygame.Surface) -> None:
        """Draw the top header bar."""
        pygame.draw.rect(screen, HEADER_BG, (0, 0, self.win_w, self.TOP_MARGIN))
        font_title = pygame.font.SysFont("Consolas", 16, bold=True)
        font_sub = pygame.font.SysFont("Consolas", 11)

        title = font_title.render("ELEVATOR FLEET DISPATCHER", True, ACCENT)
        screen.blit(title, (15, 10))

        speed_text = "PAUSED" if self.paused else f"Speed: {getattr(self, 'speed', 1.0):.2f}x"
        sub = font_sub.render(
            f"Step {self.sim.current_step}/{self.sim.total_steps}  |  {speed_text}",
            True, TEXT_DIM,
        )
        screen.blit(sub, (15, 35))

        if getattr(self, "selected_origin_floor", None) is not None:
            count = getattr(self, "pending_passenger_count", 0)
            if self.scenario_case == 2 and getattr(self, "selected_dest_floor", None) is not None:
                msg = f"[ SELECT ELEVATOR FOR {count} PAX | R-CLICK CANCEL ]"
            else:
                msg = f"[ SELECT DEST FOR {count} PAX | R-CLICK CANCEL ]"
            dest_text = font_title.render(msg, True, (255, 200, 50))
            screen.blit(dest_text, (self.win_w // 2 - dest_text.get_width() // 2, 10))

    def _draw_stats_panel(self, screen: pygame.Surface) -> None:
        """Draw the right-side stats panel."""
        px = self.shaft_x0 + self.shaft_area_w + 15
        py = self.TOP_MARGIN + 10
        pw = self.RIGHT_PANEL_W - 30
        ph = self.win_h - self.TOP_MARGIN - self.BOTTOM_MARGIN - 20

        # Panel background
        pygame.draw.rect(screen, PANEL_BG, (px, py, pw, ph), border_radius=8)
        pygame.draw.rect(screen, SHAFT_BORDER, (px, py, pw, ph), 1, border_radius=8)

        font_hdr = pygame.font.SysFont("Consolas", 13, bold=True)
        font_val = pygame.font.SysFont("Consolas", 12)
        font_sm = pygame.font.SysFont("Consolas", 10)

        y = py + 15
        x = px + 15

        # Title
        hdr = font_hdr.render("LIVE METRICS", True, ACCENT)
        screen.blit(hdr, (x, y))
        y += 28

        # Metrics
        m = self.sim.metrics
        completed = m.total_completed
        avg_wait = m.avg_wait_time
        sla_target = self.sim.weight_adjuster.sla_wait_target_sec
        sla_met = avg_wait <= sla_target

        stats = [
            ("Total Calls", str(m.total_calls)),
            ("Completed", str(completed)),
            ("Emergency", str(m.emergency_calls)),
            ("Rejections", str(m.capacity_rejections)),
            ("", ""),  # spacer
            ("Avg Wait", f"{avg_wait:.1f}s"),
            ("Max Wait", f"{m.max_wait_time:.1f}s"),
            ("SLA Target", f"{sla_target:.0f}s"),
            ("SLA Status", "MET" if sla_met else "VIOLATED"),
            ("", ""),
            ("Distance", f"{m.total_distance} floors"),
            ("Reopts", str(m.reopt_count)),
        ]

        for label, value in stats:
            if label == "":
                y += 8
                pygame.draw.line(
                    screen, SHAFT_BORDER, (x, y), (x + pw - 30, y)
                )
                y += 8
                continue

            lbl = font_val.render(label, True, TEXT_DIM)
            screen.blit(lbl, (x, y))

            # Color special values
            val_color = TEXT_WHITE
            if label == "SLA Status":
                val_color = SLA_OK if sla_met else SLA_FAIL
            elif label == "Avg Wait":
                val_color = SLA_OK if avg_wait <= sla_target else SLA_FAIL
            elif label == "Rejections" and int(value) > 0:
                val_color = SLA_WARN

            val = font_val.render(value, True, val_color)
            screen.blit(val, (x + pw - 45 - val.get_width(), y))
            y += 20

        # Elevator status section
        y += 10
        hdr2 = font_hdr.render("ELEVATORS", True, ACCENT)
        screen.blit(hdr2, (x, y))
        y += 22

        for elev in self.sim.building.elevators:
            status = elev.direction
            if not elev.is_operational:
                status = "OFFLINE"
            color_map = {
                "UP": COLOR_UP, "DOWN": COLOR_DOWN,
                "IDLE": COLOR_IDLE, "OFFLINE": COLOR_OFF,
            }
            dot_color = color_map.get(status, TEXT_DIM)
            pygame.draw.circle(screen, dot_color, (x + 6, y + 7), 5)
            info = font_sm.render(
                f"E{elev.elevator_id}: F{elev.current_floor:>2} "
                f"{status:<6} {len(elev.passengers)}p "
                f"{elev.occupancy_percent():.0f}%",
                True, TEXT_WHITE,
            )
            screen.blit(info, (x + 16, y))
            y += 17

        # Controls help at bottom
        y = py + ph - 55
        pygame.draw.line(screen, SHAFT_BORDER, (x, y), (x + pw - 30, y))
        y += 8
        controls = [
            "SPACE: Pause/Resume",
            "UP/DOWN: Speed +/-",
            "ESC: Quit",
        ]
        for line in controls:
            ctl = font_sm.render(line, True, TEXT_DIM)
            screen.blit(ctl, (x, y))
            y += 14

    def _draw_footer(self, screen: pygame.Surface) -> None:
        """Draw the bottom footer bar."""
        fy = self.win_h - self.BOTTOM_MARGIN
        pygame.draw.rect(screen, HEADER_BG, (0, fy, self.win_w, self.BOTTOM_MARGIN))

        font = pygame.font.SysFont("Consolas", 11)

        # Progress bar
        bar_x = 15
        bar_y = fy + 14
        bar_w = self.win_w - 30
        bar_h = 10
        progress = self.sim.current_step / max(self.sim.total_steps, 1)

        pygame.draw.rect(screen, SHAFT_BORDER, (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        fill_w = int(bar_w * progress)
        pygame.draw.rect(screen, ACCENT, (bar_x, bar_y, fill_w, bar_h), border_radius=4)

        # Percentage text
        pct_text = font.render(f"{progress * 100:.1f}%", True, TEXT_WHITE)
        screen.blit(pct_text, (bar_x + bar_w // 2 - pct_text.get_width() // 2, fy + 1))

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self) -> dict:
        """
        Run the simulation with Pygame visualization.

        Returns the simulation summary dict when done.
        """
        pygame.init()
        screen = pygame.display.set_mode((self.win_w, self.win_h))
        pygame.display.set_caption("Elevator Fleet Dispatcher -- Live Visualization")
        clock = pygame.time.Clock()

        from datetime import timedelta

        summary = None

        while self.running:
            # --- Events ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_SPACE:
                        self.paused = not self.paused
                    elif event.key == pygame.K_UP:
                        self.speed *= 1.5
                        self.speed = min(self.speed, self.max_speed)
                    elif event.key == pygame.K_DOWN:
                        self.speed /= 1.5
                        self.speed = max(self.speed, 0.01)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 3:  # Right click
                        self.selected_origin_floor = None
                        self.pending_passenger_count = 0
                        self.selected_dest_floor = None
                    elif event.button == 1:  # Left click
                        pos = pygame.event.get() if not pygame.mouse.get_pos() else pygame.mouse.get_pos()
                        
                        # 1. Check Elevator click for Case 2
                        if self.scenario_case == 2 and getattr(self, "selected_dest_floor", None) is not None:
                            clicked_elevator = self._get_clicked_elevator(pos)
                            if clicked_elevator is not None:
                                origin = self.selected_origin_floor
                                dest = self.selected_dest_floor
                                direction = "UP" if dest > origin else "DOWN"
                                self.sim.process_calls([(origin, direction, "NORMAL", dest, clicked_elevator)])
                                self.pending_passenger_count -= 1
                                if self.pending_passenger_count <= 0:
                                    self.selected_origin_floor = None
                                    self.pending_passenger_count = 0
                                    self.selected_dest_floor = None
                                else:
                                    self.selected_dest_floor = None
                                continue # handled!

                        # 2. Check Floor buttons
                        for f, rect in self.floor_buttons.items():
                            if rect.collidepoint(pos):
                                if getattr(self, "selected_origin_floor", None) is None or self.selected_origin_floor == f:
                                    self.selected_origin_floor = f
                                    if not hasattr(self, "pending_passenger_count"):
                                        self.pending_passenger_count = 0
                                    self.pending_passenger_count += 1
                                    self.selected_dest_floor = None
                                else:
                                    if self.scenario_case == 2:
                                        self.selected_dest_floor = f
                                    else:
                                        origin = self.selected_origin_floor
                                        dest = f
                                        if origin != dest:
                                            direction = "UP" if dest > origin else "DOWN"
                                            self.sim.process_calls([(origin, direction, "NORMAL", dest)])
                                            self.pending_passenger_count -= 1
                                            if self.pending_passenger_count <= 0:
                                                self.selected_origin_floor = None
                                                self.pending_passenger_count = 0
                                break

            # --- Simulation steps ---
            if not self.paused and self.sim.current_step < self.sim.total_steps:
                if not hasattr(self, "frame_accumulator"):
                    self.frame_accumulator = 0.0
                self.frame_accumulator += getattr(self, "speed", 1.0)
                while self.frame_accumulator >= 1.0:
                    self.frame_accumulator -= 1.0
                    if self.sim.current_step >= self.sim.total_steps:
                        break
                    step = self.sim.current_step
                    self.sim.sim_time += timedelta(
                        seconds=self.sim.time_per_step
                    )

                    calls = self.sim.generate_calls()
                    if calls:
                        self.sim.process_calls(calls)
                    self.sim.move_elevators()

                    if step % 10 == 0:
                        self.sim.reoptimize_routes()
                    if step % 30 == 0 and step > 0:
                        self.sim.adjust_weights()
                    if step % 60 == 0 and step > 0:
                        self.sim.update_prediction()
                    if step % 120 == 0:
                        self.sim.check_stuck_elevators()

                    self.sim.current_step += 1

            # Check if simulation finished
            if self.sim.current_step >= self.sim.total_steps and summary is None:
                self.sim.logger.close()
                summary = self.sim._generate_summary()
                self.sim._print_summary(summary)

            # --- Draw ---
            screen.fill(BLACK)
            self._draw_building(screen)
            self._draw_pending_calls(screen)
            self._draw_elevators(screen)
            self._draw_passengers(screen)
            self._draw_header(screen)
            self._draw_stats_panel(screen)
            self._draw_footer(screen)

            pygame.display.flip()
            clock.tick(30)

        pygame.quit()
        return summary or {}
