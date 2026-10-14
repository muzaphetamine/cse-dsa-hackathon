import csv
import sys
from collections import deque

import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.animation import FuncAnimation
from matplotlib.patches import Patch


DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]


def read_maze():
    """Read an N x N maze from a CSV file."""

    filename = input("Enter CSV filename: ").strip()

    with open(filename, newline="") as file:
        grid = [
            [cell.strip() for cell in row]
            for row in csv.reader(file)
            if row
        ]

    if not grid or not grid[0]:
        raise ValueError("Maze cannot be empty.")

    n = len(grid)

    if any(len(row) != n for row in grid):
        raise ValueError("The maze must be an N x N grid.")

    allowed = set(".#SEabcdefABCDF")

    for row in grid:
        for cell in row:
            if cell not in allowed:
                raise ValueError(f"Invalid maze cell: {cell}")

    starts = [
        (r, c) for r in range(n) for c in range(n)
        if grid[r][c] == "S"
    ]

    exits = [
        (r, c) for r in range(n) for c in range(n)
        if grid[r][c] == "E"
    ]

    if len(starts) != 1 or len(exits) != 1:
        raise ValueError("Maze needs exactly one S and one E.")

    keys = {
        cell for row in grid for cell in row
        if cell in "abcdef"
    }

    doors = {
        cell.lower() for row in grid for cell in row
        if cell in "ABCDF"
    }

    if not doors.issubset(keys):
        raise ValueError("Every door must have a matching key.")

    return grid, starts[0], exits[0]


def shortest_path(grid, start, end):
    n = len(grid)

    key_types = sorted({cell for row in grid for cell in row
                        if cell in "abcdef"})
    key_bit = {key: 1 << i for i, key in enumerate(key_types)}

    start_state = (start[0], start[1], 0)
    queue = deque([(start[0], start[1], 0, 0)])
    visited = {start_state}
    parent = {start_state: None}
    events = []

    while queue:
        r, c, mask, distance = queue.popleft()
        cell = grid[r][c]

        if cell in "abcdef":
            action = f"Collected key {cell}"
        elif cell in "ABCDF":
            action = f"Opened door {cell}"
        else:
            action = "Exploring maze"

        events.append((r, c, mask, action))

        if (r, c) == end:
            state = (r, c, mask)
            path = []

            while state is not None:
                path.append((state[0], state[1]))
                state = parent[state]

            path.reverse()
            return distance, path, key_bit, events

        for dr, dc in DIRECTIONS:
            nr, nc = r + dr, c + dc

            if not (0 <= nr < n and 0 <= nc < n):
                continue

            cell = grid[nr][nc]

            if cell == "#":
                continue

            if cell in "ABCDF":
                needed = key_bit.get(cell.lower(), 0)
                if needed == 0 or not (mask & needed):
                    continue

            new_mask = mask

            if cell in "abcdef":
                new_mask |= key_bit[cell]

            state = (nr, nc, new_mask)

            if state not in visited:
                visited.add(state)
                parent[state] = (r, c, mask)
                queue.append((nr, nc, new_mask, distance + 1))

    return -1, [], key_bit, events


def save_csv(grid, path):
    output = [row[:] for row in grid]

    for r, c in path:
        if output[r][c] == ".":
            output[r][c] = "x"

    with open("maze_solution.csv", "w", newline="") as file:
        csv.writer(file).writerows(output)

    print("Saved maze_solution.csv")


def animate_maze(grid, path, key_bit, events):
    n = len(grid)

    # Colours for maze cells
    colors = [
        "white",       # 0 open
        "black",       # 1 wall
        "limegreen",   # 2 start
        "red",      # 3 exit
        "#3498db",     # 4 key a
        "#9b59b6",     # 5 door A
        "#e67e22",     # 6 key b
        "#d35400",     # 7 door B
        "#f1c40f",     # 8 key c
        "#b7950b",     # 9 door C
        "#1abc9c",     # 10 key d
        "#117864",     # 11 door D
        "#e84393",     # 12 key e
        "#6c5ce7",     # 13 key f
        "#4834d4",     # 14 door F
        "#b2bec3",     # 15 explored cell
    ]

    codes = {
        ".": 0, "#": 1, "S": 2, "E": 3,
        "a": 4, "A": 5,
        "b": 6, "B": 7,
        "c": 8, "C": 9,
        "d": 10, "D": 11,
        "e": 12, "f": 13, "F": 14
    }

    base = [[codes[cell] for cell in row] for row in grid]
    image = [row[:] for row in base]

    fig, ax = plt.subplots(figsize=(8, 8))
    cmap = ListedColormap(colors)

    ax.imshow(image, cmap=cmap, vmin=0, vmax=len(colors) - 1)

    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticks([i - 0.5 for i in range(1, n)], minor=True)
    ax.set_yticks([i - 0.5 for i in range(1, n)], minor=True)
    ax.grid(which="minor", color="gray", linewidth=1)
    ax.tick_params(which="minor", bottom=False, left=False)

    for r in range(n):
        for c in range(n):
            ax.text(
                c, r, grid[r][c],
                ha="center", va="center",
                color="white" if grid[r][c] == "#" else "black",
                fontweight="bold", fontsize=12
            )

    current, = ax.plot([], [], "o", color="orange", markersize=14)
    route, = ax.plot([], [], color="blue", linewidth=3)
    status = ax.set_title("Starting BFS...")

    explored = set()
    frames = list(events)

    # Add frames to reveal the final shortest path.
    for i in range(1, len(path) + 1):
        r, c = path[i - 1]
        mask = 0
        for pr, pc, pmask, _ in events:
            if (pr, pc) == (r, c):
                mask = pmask
        frames.append((r, c, mask, "Shortest path found"))

    def update(index):
        r, c, mask, action = frames[index]

        if index < len(events):
            explored.add((r, c))

        image = [row[:] for row in base]

        for er, ec in explored:
            if grid[er][ec] == ".":
                image[er][ec] = 15

        # During the final phase, highlight the path.
        if index >= len(events):
            path_index = index - len(events) + 1
            for pr, pc in path[:path_index]:
                if grid[pr][pc] == ".":
                    image[pr][pc] = 4

            route.set_data(
                [pc for pr, pc in path[:path_index]],
                [pr for pr, pc in path[:path_index]]
            )
        else:
            route.set_data([], [])

        ax.images[0].set_data(image)
        current.set_data([c], [r])

        inventory = [
            key for key, bit in key_bit.items() if mask & bit
        ]

        status.set_text(
            f"{action} | Keys: {inventory or 'None'}"
        )

        return ax.images[0], current, route, status

    ax.legend(
        handles=[
            Patch(facecolor="limegreen", label="Start"),
            Patch(facecolor="tomato", label="Exit"),
            Patch(facecolor="black", label="Wall"),
            Patch(facecolor="#3498db", label="Key a"),
            Patch(facecolor="#9b59b6", label="Door A"),
            Patch(facecolor="#b2bec3", label="Explored"),
            Patch(facecolor="blue", label="Shortest path")
        ],
        loc="upper left",
        bbox_to_anchor=(1.02, 1)
    )

    plt.tight_layout()

    # Keep animation alive until the window closes.
    animation = FuncAnimation(
        fig, update, frames=len(frames),
        interval=400, repeat=False, blit=False
    )

    plt.show()


def main():
    try:
        grid, start, end = read_maze()
    except (ValueError, EOFError) as error:
        print("Input error:", error)
        return

    distance, path, key_bit, events = shortest_path(
        grid, start, end
    )

    print("Shortest path length:", distance)

    if distance == -1:
        print("No solution exists.")
        return

    print("Path coordinates (row, column):", path)
    save_csv(grid, path)
    animate_maze(grid, path, key_bit, events)


if __name__ == "__main__":
    main()