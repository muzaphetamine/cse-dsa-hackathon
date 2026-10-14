import tkinter as tk
from tkinter import ttk, messagebox
import time
import csv

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Rectangle


def read_graph(n, r, edge_text):
    graph = [set() for _ in range(n)]
    edges = []

    for line_no, line in enumerate(edge_text.strip().splitlines(), start=1):
        if not line.strip():
            continue

        parts = line.split()
        if len(parts) != 2:
            raise ValueError(f"Conflict line {line_no} must contain exactly two numbers: u v")

        try:
            u, v = map(int, parts)
        except ValueError:
            raise ValueError(f"Conflict line {line_no} must contain integers.")

        if not (1 <= u <= n and 1 <= v <= n):
            raise ValueError(f"Course numbers must be between 1 and {n}.")
        if u == v:
            raise ValueError(f"Course {u} cannot conflict with itself.")

        a, b = u - 1, v - 1
        if b not in graph[a]:
            graph[a].add(b)
            graph[b].add(a)
            edges.append((a, b))

    return graph, edges


def slot_count(slot_of):
    return max(slot_of) + 1 if slot_of else 0


def slots_from(slot_of):
    slots = [[] for _ in range(slot_count(slot_of))]
    for course, slot in enumerate(slot_of):
        slots[slot].append(course)
    return slots


def verify(graph, slot_of, r):
    if len(slot_of) != len(graph) or any(s < 0 for s in slot_of):
        return False
    for course, neighbours in enumerate(graph):
        for neighbour in neighbours:
            if slot_of[course] == slot_of[neighbour]:
                return False
    return all(len(courses) <= r for courses in slots_from(slot_of))


def welsh_powell(graph, r):
    start = time.perf_counter()
    n = len(graph)
    order = sorted(range(n), key=lambda v: (-len(graph[v]), v))
    slot_of = [-1] * n
    slot = 0

    while -1 in slot_of:
        size = 0
        for course in order:
            if slot_of[course] != -1 or size >= r:
                continue
            if all(slot_of[other] != slot or other not in graph[course]
                   for other in range(n)):
                slot_of[course] = slot
                size += 1
        slot += 1

    return {
        "name": "Welsh–Powell",
        "slot_of": slot_of,
        "slots": slot_count(slot_of),
        "time_ms": (time.perf_counter() - start) * 1000,
        "order": order,
    }


def dsatur(graph, r):
    start = time.perf_counter()
    n = len(graph)
    slot_of = [-1] * n
    slot_courses = []
    order = []

    for _ in range(n):
        unassigned = [v for v in range(n) if slot_of[v] == -1]

        def priority(v):
            neighbour_slots = {
                slot_of[u] for u in graph[v] if slot_of[u] != -1
            }
            return len(neighbour_slots), len(graph[v]), -v

        course = max(unassigned, key=priority)
        chosen = None

        for slot, courses in enumerate(slot_courses):
            if len(courses) < r and all(other not in graph[course] for other in courses):
                chosen = slot
                break

        if chosen is None:
            chosen = len(slot_courses)
            slot_courses.append([])

        slot_of[course] = chosen
        slot_courses[chosen].append(course)
        order.append(course)

    return {
        "name": "DSatur",
        "slot_of": slot_of,
        "slots": slot_count(slot_of),
        "time_ms": (time.perf_counter() - start) * 1000,
        "order": order,
    }


def exact_backtracking(graph, r, initial, timeout=5.0):
    start = time.perf_counter()
    n = len(graph)
    best = initial[:]
    upper = slot_count(best)
    lower = (n + r - 1) // r
    deadline = start + timeout
    timed_out = False
    nodes = 0

    def find_schedule(k):
        nonlocal nodes
        slot_of = [-1] * n
        slot_courses = [[] for _ in range(k)]

        def search(assigned, used_slots):
            nonlocal nodes
            nodes += 1
            if time.perf_counter() > deadline:
                raise TimeoutError
            if assigned == n:
                return slot_of[:]

            best_course = None
            best_options = None

            for course in range(n):
                if slot_of[course] != -1:
                    continue

                options = []
                for slot in range(min(used_slots + 1, k)):
                    if len(slot_courses[slot]) >= r:
                        continue
                    if any(other in graph[course] for other in slot_courses[slot]):
                        continue
                    options.append(slot)

                if not options:
                    return None

                if (best_options is None or len(options) < len(best_options)
                        or (len(options) == len(best_options)
                            and len(graph[course]) > len(graph[best_course]))):
                    best_course = course
                    best_options = options

            for slot in best_options:
                is_new = slot == used_slots
                slot_of[best_course] = slot
                slot_courses[slot].append(best_course)
                result = search(assigned + 1, used_slots + int(is_new))
                if result is not None:
                    return result
                slot_courses[slot].pop()
                slot_of[best_course] = -1

            return None

        return search(0, 0)

    try:
        for k in range(lower, upper):
            result = find_schedule(k)
            if result is not None:
                best = result
                upper = k
                break
    except TimeoutError:
        timed_out = True

    return {
        "name": "Exact backtracking",
        "slot_of": best,
        "slots": slot_count(best),
        "time_ms": (time.perf_counter() - start) * 1000,
        "order": list(range(n)),
        "proven": not timed_out,
        "timed_out": timed_out,
        "nodes": nodes,
    }


class TimetableApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Exam Timetable Scheduler | Graph Colouring Lab")
        self.root.geometry("1250x740")
        self.root.minsize(100, 650)
        self.root.configure(bg="#f3f5f9")

        self.graph = []
        self.edges = []
        self.results = []
        self.best = None
        self.animation_after_id = None

        self._build_ui()

    def _build_ui(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("Title.TLabel", font=("Segoe UI", 19, "bold"),
                        background="#f3f5f9", foreground="#182238")
        style.configure("Sub.TLabel", font=("Segoe UI", 10),
                        background="#f3f5f9", foreground="#5e6b82")
        style.configure("Panel.TLabelframe", background="white")
        style.configure("Panel.TLabelframe.Label", font=("Segoe UI", 11, "bold"),
                        foreground="#24324a", background="white")
        style.configure("Run.TButton", font=("Segoe UI", 10, "bold"), padding=8)

        header = ttk.Frame(self.root, padding=(18, 14, 18, 8))
        header.pack(fill="x")
        ttk.Label(header, text="Exam Timetable Scheduler", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Enter the conflict graph, watch it form, compare algorithms, and inspect the timetable.",
            style="Sub.TLabel"
        ).pack(anchor="w", pady=(3, 0))

        input_panel = ttk.LabelFrame(self.root, text="Input", style="Panel.TLabelframe", padding=12)
        input_panel.pack(fill="x", padx=18, pady=(4, 12))

        fields = ttk.Frame(input_panel)
        fields.pack(fill="x")

        self.n_var = tk.StringVar()
        self.m_var = tk.StringVar()
        self.r_var = tk.StringVar()
        for label, var, width in [
            ("N · Courses", self.n_var, 8),
            ("M · Conflicts", self.m_var, 8),
            ("R · Max courses per slot", self.r_var, 10),
        ]:
            field = ttk.Frame(fields)
            field.pack(side="left", padx=(0, 14))
            ttk.Label(field, text=label).pack(anchor="w")
            ttk.Entry(field, textvariable=var, width=width).pack(anchor="w", pady=(4, 0))

        edge_box = ttk.Frame(fields)
        edge_box.pack(side="left", fill="x", expand=True, padx=(0, 14))
        ttk.Label(edge_box, text="Conflict edges · one u v pair per line").pack(anchor="w")
        self.edges_text = tk.Text(edge_box, height=5, width=42, font=("Consolas", 10),
                                  wrap="none", undo=True, relief="solid", bd=1)
        self.edges_text.pack(fill="x", expand=True, pady=(4, 0))

        actions = ttk.Frame(fields)
        actions.pack(side="left", anchor="s")
        ttk.Button(actions, text="Run scheduler", style="Run.TButton",
                   command=self.run_scheduler).pack(fill="x", pady=(0, 6))
        ttk.Button(actions, text="Load example",
                   command=self.load_example).pack(fill="x")
        ttk.Button(actions, text="Export CSV",
                   command=self.export_csv).pack(fill="x", pady=(6, 0))

        self.status_var = tk.StringVar(value="Ready. Enter the course count, conflict count, capacity, and edges.")
        ttk.Label(self.root, textvariable=self.status_var, style="Sub.TLabel").pack(
            anchor="w", padx=20, pady=(0, 8)
        )

        panels = ttk.Frame(self.root)
        panels.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        panels.columnconfigure(0, weight=1, uniform="panel")
        panels.columnconfigure(1, weight=1, uniform="panel")
        panels.columnconfigure(2, weight=1, uniform="panel")
        panels.rowconfigure(0, weight=1)

        graph_frame = ttk.LabelFrame(panels, text="1 · Animated graph formation", padding=8)
        compare_frame = ttk.LabelFrame(panels, text="2 · Algorithm vs execution time", padding=8)
        timetable_frame = ttk.LabelFrame(panels, text="3 · Final timetable", padding=8)
        graph_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        compare_frame.grid(row=0, column=1, sticky="nsew", padx=4)
        timetable_frame.grid(row=0, column=2, sticky="nsew", padx=(7, 0))

        self.graph_fig, self.graph_ax = plt.subplots(figsize=(4, 4))
        self.graph_canvas = FigureCanvasTkAgg(self.graph_fig, master=graph_frame)
        self.graph_canvas.get_tk_widget().pack(fill="both", expand=True)

        self.compare_fig, self.compare_ax = plt.subplots(figsize=(4, 4))
        self.compare_canvas = FigureCanvasTkAgg(self.compare_fig, master=compare_frame)
        self.compare_canvas.get_tk_widget().pack(fill="both", expand=True)

        self.table_frame = ttk.Frame(timetable_frame)
        self.table_frame.pack(fill="both", expand=True)
        self.table_text = tk.Text(self.table_frame, font=("Consolas", 10), wrap="none",
                                  relief="flat", bg="white", state="disabled")
        self.table_text.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.table_text.yview)
        scroll.pack(side="right", fill="y")
        self.table_text.configure(yscrollcommand=scroll.set)

        self.graph_ax.set_title("Graph will appear here")
        self.graph_ax.axis("off")
        self.graph_canvas.draw()
        self.compare_ax.set_title("Run the scheduler to compare algorithms")
        self.compare_ax.axis("off")
        self.compare_canvas.draw()

    def load_example(self):
        self.n_var.set("6")
        self.m_var.set("7")
        self.r_var.set("3")
        self.edges_text.delete("1.0", "end")
        self.edges_text.insert("1.0", "1 2\n1 3\n2 3\n2 4\n3 5\n4 5\n5 6")
        self.status_var.set("Example loaded. Click Run scheduler.")

    def run_scheduler(self):
        if self.animation_after_id is not None:
            self.root.after_cancel(self.animation_after_id)
            self.animation_after_id = None

        try:
            n = int(self.n_var.get())
            m = int(self.m_var.get())
            r = int(self.r_var.get())
            if n < 1:
                raise ValueError("N must be at least 1.")
            if m < 0:
                raise ValueError("M cannot be negative.")
            if r < 1:
                raise ValueError("R must be at least 1.")

            edge_lines = [line for line in self.edges_text.get("1.0", "end").splitlines()
                          if line.strip()]
            if len(edge_lines) != m:
                raise ValueError(f"M is {m}, but you entered {len(edge_lines)} conflict lines.")

            graph, edges = read_graph(n, r, "\n".join(edge_lines))
        except ValueError as error:
            messagebox.showerror("Invalid input", str(error))
            return

        self.graph, self.edges = graph, edges
        wp = welsh_powell(graph, r)
        ds = dsatur(graph, r)
        warm = wp if wp["slots"] <= ds["slots"] else ds
        exact = exact_backtracking(graph, r, warm["slot_of"], timeout=5.0)
        self.results = [wp, ds, exact]

        for result in self.results:
            if not verify(graph, result["slot_of"], r):
                messagebox.showerror("Algorithm error", f"{result['name']} produced an invalid timetable.")
                return

        self.best = min(self.results, key=lambda result: result["slots"])

        # Reveal each result only after the previous visualization has finished.
        self.compare_ax.clear()
        self.compare_ax.set_title("Waiting for graph animation…")
        self.compare_ax.axis("off")
        self.compare_canvas.draw()
        self.table_text.configure(state="normal")
        self.table_text.delete("1.0", "end")
        self.table_text.insert("1.0", "Timetable will appear after the algorithm comparison…")
        self.table_text.configure(state="disabled")

        note = "minimum proven" if exact["proven"] else "exact search timed out; best valid schedule shown"
        self.status_var.set(
            f"Step 1/3 · Building conflict graph · {len(edges)} unique conflicts · exact solver: {note}"
        )
        self._start_graph_animation(on_complete=self._start_comparison_animation)

    def _make_network(self):
        graph = nx.Graph()
        graph.add_nodes_from(range(len(self.graph)))
        graph.add_edges_from(self.edges)
        positions = nx.spring_layout(graph, seed=7)
        return graph, positions

    def _start_graph_animation(self, on_complete=None):
        graph, positions = self._make_network()
        order = self.best["order"]
        # Use the final timetable's slot colours, revealing one course at a time.
        slot_of = self.best["slot_of"]
        k = slot_count(slot_of)
        cmap = plt.get_cmap("tab20" if k <= 20 else "hsv")
        colors = [cmap(i if k <= 20 else i / k) for i in range(k)]

        self.graph_ax.clear()
        self.graph_ax.set_title("Building conflict graph…")
        self.graph_ax.axis("off")
        self.graph_canvas.draw()

        def frame(step):
            self.graph_ax.clear()
            visible = set(order[:step])
            visible_edges = [(u, v) for u, v in self.edges if u in visible and v in visible]
            graph_visible = nx.Graph()
            graph_visible.add_nodes_from(visible)
            graph_visible.add_edges_from(visible_edges)

            nx.draw_networkx_edges(graph_visible, positions, ax=self.graph_ax,
                                   edgelist=visible_edges, alpha=0.55, width=1.5)
            if visible:
                nx.draw_networkx_nodes(
                    graph_visible, positions, ax=self.graph_ax,
                    nodelist=list(visible),
                    node_color=[colors[slot_of[v]] for v in visible],
                    node_size=650, edgecolors="#263246", linewidths=1.2
                )
                nx.draw_networkx_labels(
                    graph_visible, positions,
                    labels={v: str(v + 1) for v in visible},
                    ax=self.graph_ax, font_size=10, font_weight="bold"
                )

            self.graph_ax.set_title(
                f"Graph formation · course {step}/{len(order)}" if step
                else "Graph formation · starting"
            )
            self.graph_ax.axis("off")
            self.graph_fig.tight_layout()
            self.graph_canvas.draw()

            if step < len(order):
                self.animation_after_id = self.root.after(650, lambda: frame(step + 1))
            else:
                self.animation_after_id = None
                self.graph_ax.set_title(
                    f"Complete conflict graph · {len(self.graph)} courses, {len(self.edges)} edges"
                )
                self.graph_canvas.draw()
                if on_complete is not None:
                    self.status_var.set("Step 2/3 · Animating algorithm execution-time comparison…")
                    self.root.after(500, on_complete)

        frame(0)

    def _start_comparison_animation(self):
        """Animate the comparison bars only after graph formation is complete."""
        self.compare_ax.clear()
        names = [result["name"] for result in self.results]
        times = [max(result["time_ms"], 0.001) for result in self.results]
        bars = self.compare_ax.bar(names, [0.001] * len(times))
        self.compare_ax.set_title("Execution time by algorithm")
        self.compare_ax.set_ylabel("Time (milliseconds)")
        self.compare_ax.set_yscale("log")
        self.compare_ax.set_ylim(0.0005, max(times) * 1.8)
        self.compare_ax.tick_params(axis="x", rotation=20, labelsize=8)
        self.compare_ax.grid(axis="y", alpha=0.25)
        self.compare_fig.tight_layout()
        self.compare_canvas.draw()

        frames = 24
        minimum_height = 0.001

        def animate(frame_number):
            progress = frame_number / frames
            # Ease-out makes the bars slow down as they reach their final values.
            eased = 1 - (1 - progress) ** 2
            for bar, result, target in zip(bars, self.results, times):
                bar.set_height(minimum_height + (target - minimum_height) * eased)
            self.compare_canvas.draw_idle()

            if frame_number < frames:
                self.animation_after_id = self.root.after(
                    45, lambda: animate(frame_number + 1)
                )
            else:
                self.animation_after_id = None
                for bar, result in zip(bars, self.results):
                    self.compare_ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        bar.get_height(),
                        f"{result['time_ms']:.2f} ms\n{result['slots']} slots",
                        ha="center", va="bottom", fontsize=8
                    )
                self.compare_fig.tight_layout()
                self.compare_canvas.draw()
                self.status_var.set("Step 3/3 · Loading final timetable…")
                self.root.after(450, self._finish_visualization_sequence)

        animate(0)

    def _finish_visualization_sequence(self):
        self._draw_timetable()
        note = "minimum proven" if self.results[2]["proven"] else "exact search timed out; best valid schedule shown"
        self.status_var.set(
            f"Complete · {self.best['slots']} slots · {len(self.edges)} unique conflicts · exact solver: {note}"
        )

    def _draw_comparison(self):
        self.compare_ax.clear()
        names = [result["name"] for result in self.results]
        times = [max(result["time_ms"], 0.001) for result in self.results]
        bars = self.compare_ax.bar(names, times)
        self.compare_ax.set_title("Execution time by algorithm")
        self.compare_ax.set_ylabel("Time (milliseconds)")
        self.compare_ax.set_yscale("log")
        self.compare_ax.tick_params(axis="x", rotation=20, labelsize=8)
        self.compare_ax.grid(axis="y", alpha=0.25)
        for bar, result in zip(bars, self.results):
            self.compare_ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"{result['time_ms']:.2f} ms\n{result['slots']} slots",
                ha="center", va="bottom", fontsize=8
            )
        self.compare_fig.tight_layout()
        self.compare_canvas.draw()

    def _draw_timetable(self):
        self.table_text.configure(state="normal")
        self.table_text.delete("1.0", "end")
        lines = [
            f"Best result: {self.best['name']}",
            f"Time slots: {self.best['slots']}",
            "",
        ]

        for number, courses in enumerate(slots_from(self.best["slot_of"]), start=1):
            lines.append(f"SLOT {number}")
            lines.append("-" * 24)
            if courses:
                lines.extend(f"  Course {course + 1}" for course in courses)
            else:
                lines.append("  (empty)")
            lines.append("")

        lines.extend(["ALGORITHM SUMMARY", "=" * 24])
        for result in self.results:
            marker = " *" if result is self.best else ""
            lines.append(f"{result['name']}{marker}")
            lines.append(f"  Slots: {result['slots']}")
            lines.append(f"  Time:  {result['time_ms']:.3f} ms")
            if result["name"] == "Exact backtracking":
                lines.append(f"  Optimality proven: {result['proven']}")
            lines.append("")

        self.table_text.insert("1.0", "\n".join(lines))
        self.table_text.configure(state="disabled")

    def export_csv(self):
        if self.best is None:
            messagebox.showinfo("No timetable yet", "Run the scheduler first.")
            return

        slots = slots_from(self.best["slot_of"])
        max_courses = max((len(slot) for slot in slots), default=0)
        try:
            with open("timetable.csv", "w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(["Time Slot"] + [f"Course {i + 1}" for i in range(max_courses)])
                for number, courses in enumerate(slots, start=1):
                    row = [f"Slot {number}"] + [course + 1 for course in courses]
                    row += [""] * (max_courses - len(courses))
                    writer.writerow(row)
            messagebox.showinfo("CSV exported", "Saved timetable.csv in the current working directory.")
        except OSError as error:
            messagebox.showerror("Export failed", str(error))


if __name__ == "__main__":
    root = tk.Tk()
    app = TimetableApp(root)
    root.mainloop()
