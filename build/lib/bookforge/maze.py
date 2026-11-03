"""Solvable mazes, generated in code (an image model cannot be trusted to draw one that works).

A perfect maze (exactly one path between any two cells) from a seeded depth-first search; entry at the
top-left cell, exit at the bottom-right. `draw` renders it with ReportLab onto a canvas region.
"""
from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass

N, S, E, W = 1, 2, 4, 8
MOVE = {N: (0, -1), S: (0, 1), E: (1, 0), W: (-1, 0)}
OPP = {N: S, S: N, E: W, W: E}


@dataclass
class Maze:
    cols: int
    rows: int
    open: list[list[int]]  # open[y][x]: bitmask of the walls removed around that cell

    @property
    def start(self) -> tuple[int, int]:
        return 0, 0

    @property
    def goal(self) -> tuple[int, int]:
        return self.cols - 1, self.rows - 1

    def solve(self) -> list[tuple[int, int]]:
        """Shortest path from start to goal (cells as (x, y)); empty if none."""
        prev = {self.start: None}
        q = deque([self.start])
        while q:
            c = q.popleft()
            if c == self.goal:
                break
            x, y = c
            for d, (dx, dy) in MOVE.items():
                n = (x + dx, y + dy)
                if self.open[y][x] & d and n not in prev:
                    prev[n] = c
                    q.append(n)
        if self.goal not in prev:
            return []
        path, c = [], self.goal
        while c is not None:
            path.append(c)
            c = prev[c]
        return path[::-1]


def generate(cols: int = 10, rows: int = 12, seed: int = 1) -> Maze:
    rnd = random.Random(seed)
    grid = [[0] * cols for _ in range(rows)]
    seen = {(0, 0)}
    stack = [(0, 0)]
    while stack:
        x, y = stack[-1]
        options = [(d, x + dx, y + dy) for d, (dx, dy) in MOVE.items()
                   if 0 <= x + dx < cols and 0 <= y + dy < rows and (x + dx, y + dy) not in seen]
        if not options:
            stack.pop()
            continue
        d, nx, ny = rnd.choice(options)
        grid[y][x] |= d
        grid[ny][nx] |= OPP[d]
        seen.add((nx, ny))
        stack.append((nx, ny))
    return Maze(cols, rows, grid)


def draw(c, m: Maze, x0: float, y0: float, w: float, h: float, line: float = 3.0,
         solution: bool = False, color=(0.15, 0.15, 0.2), path_color=(0.55, 0.2, 0.75)) -> tuple[float, float]:
    """Draw the maze in the box (x0, y0 bottom-left, w x h, PDF points). Returns the cell size used.
    Openings: the top edge of the start cell and the bottom edge of the goal cell."""
    cell = min(w / m.cols, h / m.rows)
    ox = x0 + (w - cell * m.cols) / 2
    oy = y0 + (h - cell * m.rows) / 2
    top = oy + cell * m.rows

    def px(x, y):  # grid corner (x, y), y downward -> PDF point
        return ox + x * cell, top - y * cell

    c.saveState()
    c.setStrokeColorRGB(*color)
    c.setLineWidth(line)
    c.setLineCap(1)
    for y in range(m.rows):
        for x in range(m.cols):
            o = m.open[y][x]
            if not o & N and not (x, y) == m.start:
                c.line(*px(x, y), *px(x + 1, y))
            if not o & W:
                c.line(*px(x, y), *px(x, y + 1))
            if x == m.cols - 1 and not o & E:
                c.line(*px(x + 1, y), *px(x + 1, y + 1))
            if y == m.rows - 1 and not o & S and not (x, y) == m.goal:
                c.line(*px(x, y + 1), *px(x + 1, y + 1))
    if solution:
        c.setStrokeColorRGB(*path_color)
        c.setLineWidth(max(line, cell * 0.22))
        pts = [px(x + 0.5, y + 0.5) for x, y in m.solve()]
        p = c.beginPath()
        p.moveTo(*pts[0])
        for q in pts[1:]:
            p.lineTo(*q)
        c.drawPath(p, stroke=1, fill=0)
    c.restoreState()
    return cell, cell
