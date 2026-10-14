import csv
import heapq
import html
import math
import os

CSV_FILE = "budget_traveller_output.csv"
SVG_FILE = "budget_traveller_graph.svg"


def find_route(n, flights, max_stops, coupons_available):
    """Dijkstra on (city, flights taken, coupons used). Coupon halves fare with floor."""
    max_flights = min(max(0, n - 1), max_stops + 1)
    graph = [[] for _ in range(n + 1)]
    for edge_id, (u, v, price) in enumerate(flights):
        graph[u].append((v, price, edge_id))

    start = (1, 0, 0)
    dist = {start: 0}
    parent = {}
    heap = [(0, 1, 0, 0)]
    destination_state = None

    while heap:
        cost, city, flights_used, coupons_used = heapq.heappop(heap)
        state = (city, flights_used, coupons_used)
        if cost != dist.get(state):
            continue
        if city == n:
            destination_state = state
            break
        if flights_used >= max_flights:
            continue

        for nxt, price, edge_id in graph[city]:
            next_state = (nxt, flights_used + 1, coupons_used)
            next_cost = cost + price
            if next_cost < dist.get(next_state, float("inf")):
                dist[next_state] = next_cost
                parent[next_state] = (state, edge_id, False, price, price)
                heapq.heappush(heap, (next_cost, *next_state))

            if coupons_used < coupons_available:
                discounted = price // 2
                coupon_state = (nxt, flights_used + 1, coupons_used + 1)
                coupon_cost = cost + discounted
                if coupon_cost < dist.get(coupon_state, float("inf")):
                    dist[coupon_state] = coupon_cost
                    parent[coupon_state] = (state, edge_id, True, price, discounted)
                    heapq.heappush(heap, (coupon_cost, *coupon_state))

    if destination_state is None:
        return None, []

    steps = []
    state = destination_state
    while state != start:
        prior, edge_id, coupon, original, final = parent[state]
        steps.append({
            "source": prior[0], "destination": state[0], "price": original,
            "final_price": final, "coupon": coupon, "edge_id": edge_id,
            "flights_taken": state[1], "stops_used": max(0, state[1] - 1),
            "coupons_used": state[2], "running_cost": dist[state]
        })
        state = prior
    steps.reverse()
    return dist[destination_state], steps


def write_csv(flights, route_steps):
    route_map = {s["edge_id"]: s for s in route_steps}
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Source", "Destination", "Original Price", "On Optimal Route", "Coupon Used", "Final Price"])
        for edge_id, (u, v, price) in enumerate(flights):
            step = route_map.get(edge_id)
            if step:
                writer.writerow([u, v, price, "Yes", "Yes" if step["coupon"] else "No", step["final_price"]])
            else:
                writer.writerow([u, v, price, "No", "No", price])


def build_svg(n, flights, route_steps, min_cost, coupons_available):
    width, height = 1000, 700
    radius = 28
    if n == 1:
        positions = {1: (500.0, 300.0)}
    else:
        positions = {}
        for city in range(1, n + 1):
            angle = -math.pi / 2 + 2 * math.pi * (city - 1) / n
            positions[city] = (500 + 345 * math.cos(angle), 305 + 205 * math.sin(angle))

    route_map = {s["edge_id"]: s for s in route_steps}
    elements = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<title>Budget Traveller Animated Journey</title>
<defs>
 <marker id="arrow-gray" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#9ca3af"/></marker>
 <marker id="arrow-blue" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#2563eb"/></marker>
 <marker id="arrow-gold" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#d4a017"/></marker>
 <style>
 text {{font-family:Arial,sans-serif}}
 .edge {{fill:none;stroke:#9ca3af;stroke-width:2.2;marker-end:url(#arrow-gray)}}
 .route-edge {{fill:none;stroke:#2563eb;stroke-width:4;marker-end:url(#arrow-blue)}}
 .coupon-edge {{fill:none;stroke:#d4a017;stroke-width:5;marker-end:url(#arrow-gold)}}
 .city {{stroke-width:2.5}}
 .city-start {{fill:#22c55e;stroke:#15803d}}
 .city-destination {{fill:#ef4444;stroke:#b91c1c}}
 .city-intermediate {{fill:#f59e0b;stroke:#b45309}}
 .city-other {{fill:#eff6ff;stroke:#2563eb}}
 .city-label {{font-size:17px;font-weight:bold;fill:#1e293b;text-anchor:middle;dominant-baseline:middle}}
 .edge-label {{font-size:13px;font-weight:bold;fill:#1f2937;text-anchor:middle}}
 .panel {{fill:#f8fafc;stroke:#cbd5e1;stroke-width:1.5}}
 .panel-title {{font-size:18px;font-weight:bold;fill:#111827}}
 .panel-text {{font-size:15px;fill:#374151}}
 .small {{font-size:13px;fill:#4b5563}}
 </style>
</defs>
<rect width="100%" height="100%" fill="white"/>
<text x="35" y="38" font-size="25" font-weight="bold" fill="#111827">Budget Traveller — Animated Journey</text>
<text x="35" y="63" font-size="14" fill="#6b7280">Green = start · Red = destination · Orange = intermediate stop · Blue = route · Gold = coupon · Grey = other flights</text>
''']

    # Render all directed edges and labels.
    for edge_id, (u, v, price) in enumerate(flights):
        x1, y1 = positions[u]
        x2, y2 = positions[v]
        if u == v:
            path = f"M {x1-13:.1f} {y1-20:.1f} C {x1-65:.1f} {y1-85:.1f}, {x1+65:.1f} {y1-85:.1f}, {x1+13:.1f} {y1-20:.1f}"
            lx, ly = x1, y1 - 72
        else:
            dx, dy = x2 - x1, y2 - y1
            length = math.hypot(dx, dy) or 1
            ux, uy = dx / length, dy / length
            nx, ny = -uy, ux
            reverse = any(a == v and b == u for a, b, _ in flights)
            offset = (9 if u < v else -9) if reverse else 0
            sx, sy = x1 + ux * radius + nx * offset, y1 + uy * radius + ny * offset
            ex, ey = x2 - ux * (radius + 7) + nx * offset, y2 - uy * (radius + 7) + ny * offset
            path = f"M {sx:.1f} {sy:.1f} L {ex:.1f} {ey:.1f}"
            lx, ly = (sx + ex) / 2 + nx * (12 if offset >= 0 else -12), (sy + ey) / 2 + ny * (12 if offset >= 0 else -12)
        step = route_map.get(edge_id)
        if step and step["coupon"]:
            css_class = "coupon-edge"
            label = f'{price} → {step["final_price"]} COUPON'
            border = "#eab308"
        elif step:
            css_class = "route-edge"
            label = str(price)
            border = "#93c5fd"
        else:
            css_class = "edge"
            label = str(price)
            border = "#d1d5db"
        elements.append(f'<path id="edge-{edge_id}" class="{css_class}" d="{path}"/>')
        box_width = max(42, len(label) * 7 + 14)
        elements.append(f'<rect x="{lx-box_width/2:.1f}" y="{ly-12:.1f}" width="{box_width:.1f}" height="24" rx="6" fill="white" stroke="{border}"/>')
        elements.append(f'<text class="edge-label" x="{lx:.1f}" y="{ly+4:.1f}">{html.escape(label)}</text>')

    route_cities = set()
    for step in route_steps:
        route_cities.update((step["source"], step["destination"]))
    for city, (x, y) in positions.items():
        # Required node colours: start green, destination red, route intermediates orange.
        if city == 1:
            node_class = "city city-start"
        elif city == n:
            node_class = "city city-destination"
        elif city in route_cities:
            node_class = "city city-intermediate"
        else:
            node_class = "city city-other"
        elements.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius}" class="{node_class}"/>')
        elements.append(f'<text x="{x:.1f}" y="{y:.1f}" class="city-label">{city}</text>')

    # Progress panel and controls.
    elements.append('''
<rect x="35" y="515" width="930" height="140" rx="14" class="panel"/>
<text x="58" y="545" class="panel-title" id="status-title">Ready to start</text>
<text x="58" y="572" class="panel-text" id="status-city">Current City: 1</text>
<text x="58" y="598" class="panel-text" id="status-cost">Running Cost: 0</text>
<text x="350" y="572" class="panel-text" id="status-flights">Flights Taken: 0</text>
<text x="350" y="598" class="panel-text" id="status-stops">Stops Used: 0</text>
<text x="650" y="572" class="panel-text" id="status-coupons">Coupons Used: 0</text>
<text x="650" y="598" class="panel-text" id="status-min">Minimum Cost: —</text>
<text x="58" y="630" class="small" id="status-detail">Press Play to animate the computed optimal route.</text>
<circle id="traveller-dot" cx="500" cy="300" r="9" fill="#2563eb" stroke="white" stroke-width="3"/>
<g font-size="14" font-weight="bold">
 <rect x="685" y="78" width="88" height="35" rx="8" fill="#2563eb"/><text x="729" y="100" text-anchor="middle" fill="white">▶ Play</text>
 <rect x="785" y="78" width="88" height="35" rx="8" fill="#64748b"/><text x="829" y="100" text-anchor="middle" fill="white">Ⅱ Pause</text>
 <rect x="885" y="78" width="83" height="35" rx="8" fill="#0f766e"/><text x="926" y="100" text-anchor="middle" fill="white">↻ Replay</text>
 <rect id="play-hit" x="685" y="78" width="88" height="35" rx="8" fill="transparent" style="cursor:pointer"/>
 <rect id="pause-hit" x="785" y="78" width="88" height="35" rx="8" fill="transparent" style="cursor:pointer"/>
 <rect id="replay-hit" x="885" y="78" width="83" height="35" rx="8" fill="transparent" style="cursor:pointer"/>
</g>
''')

    # JavaScript data uses only values computed by the algorithm.
    js_steps = []
    for step in route_steps:
        x1, y1 = positions[step["source"]]
        x2, y2 = positions[step["destination"]]
        js_steps.append("{" + ",".join([
            f'source:{step["source"]}', f'destination:{step["destination"]}',
            f'price:{step["price"]}', f'finalPrice:{step["final_price"]}',
            f'coupon:{str(step["coupon"]).lower()}', f'runningCost:{step["running_cost"]}',
            f'flightsTaken:{step["flights_taken"]}', f'stopsUsed:{step["stops_used"]}',
            f'couponsUsed:{step["coupons_used"]}', f'edgeId:{step["edge_id"]}',
            f'x1:{x1:.2f}', f'y1:{y1:.2f}', f'x2:{x2:.2f}', f'y2:{y2:.2f}'
        ]) + "}")
    steps_js = ",".join(js_steps)
    start_x, start_y = positions[1]
    total_js = "null" if min_cost is None else str(min_cost)
    route_text = " → ".join([str(1)] + [str(s["destination"]) for s in route_steps]) if route_steps else ("1" if n == 1 else "No route")
    route_text_js = route_text.replace("\\", "\\\\").replace("'", "\\'")
    elements.append(f'''<script><![CDATA[
(function() {{
 const steps = [{steps_js}];
 const totalCost = {total_js};
 const routeText = '{route_text_js}';
 const startX = {start_x:.2f}, startY = {start_y:.2f};
 let index = 0, progress = 0, playing = false, frameId = null, lastTime = 0;
 const el = id => document.getElementById(id);
 const dot = el('traveller-dot');
 function status(step) {{
   if (!step) {{
     el('status-title').textContent = steps.length ? 'Ready to start' : 'No route found';
     el('status-city').textContent = 'Current City: 1';
     el('status-cost').textContent = 'Running Cost: 0';
     el('status-flights').textContent = 'Flights Taken: 0';
     el('status-stops').textContent = 'Stops Used: 0';
     el('status-coupons').textContent = 'Coupons Used: 0 / {coupons_available}';
     el('status-min').textContent = 'Minimum Cost: ' + (totalCost === null ? 'No route' : totalCost);
     el('status-detail').textContent = steps.length ? 'Press Play to animate the computed optimal route.' : 'No valid route exists within the stop limit.';
     return;
   }}
   el('status-title').textContent = index >= steps.length ? 'Journey complete!' : 'Journey in progress';
   el('status-city').textContent = 'Current City: ' + step.destination;
   el('status-cost').textContent = 'Running Cost: ' + step.runningCost;
   el('status-flights').textContent = 'Flights Taken: ' + step.flightsTaken;
   el('status-stops').textContent = 'Stops Used: ' + step.stopsUsed;
   el('status-coupons').textContent = 'Coupons Used: ' + step.couponsUsed + ' / {coupons_available}';
   el('status-min').textContent = 'Minimum Cost: ' + (totalCost === null ? 'No route' : totalCost);
   el('status-detail').textContent = step.coupon
     ? ('Coupon applied: ' + step.price + ' → ' + step.finalPrice + ' (COUPON)')
     : ('Flight ' + step.source + ' → ' + step.destination + ': ' + step.price);
   if (index >= steps.length) el('status-detail').textContent = 'Optimal route: ' + routeText + ' | Minimum cost: ' + totalCost;
 }}
 function setDot(x, y) {{ dot.setAttribute('cx', x); dot.setAttribute('cy', y); }}
 function pause() {{ playing = false; if (frameId !== null) cancelAnimationFrame(frameId); frameId = null; }}
 function reset() {{ pause(); index = 0; progress = 0; lastTime = 0; setDot(startX, startY); status(null); }}
 function animate(now) {{
   if (!playing) return;
   if (!lastTime) lastTime = now;
   progress += (now - lastTime) / 1300;
   lastTime = now;
   if (index >= steps.length) {{ pause(); status(steps.length ? steps[steps.length - 1] : null); return; }}
   const step = steps[index];
   const t = Math.min(progress, 1);
   setDot(step.x1 + (step.x2 - step.x1) * t, step.y1 + (step.y2 - step.y1) * t);
   if (progress >= 1) {{
     setDot(step.x2, step.y2);
     index += 1; progress = 0;
     // Keep the travelled segment emphasized; coupon edges remain gold.
     const edge = el('edge-' + step.edgeId);
     if (edge) edge.setAttribute('stroke-width', step.coupon ? '6' : '5');
     status(step);
     if (index >= steps.length) {{ pause(); return; }}
   }}
   frameId = requestAnimationFrame(animate);
 }}
 function play() {{
   if (playing || steps.length === 0) return;
   if (index >= steps.length) reset();
   playing = true; lastTime = 0; frameId = requestAnimationFrame(animate);
 }}
 el('play-hit').addEventListener('click', play);
 el('pause-hit').addEventListener('click', pause);
 el('replay-hit').addEventListener('click', function() {{ reset(); play(); }});
 setDot(startX, startY); status(null);
}})();
]]></script>
</svg>''')
    with open(SVG_FILE, "w", encoding="utf-8") as file:
        file.write("\n".join(elements))


def main():
    try:
        first = input("Enter N M: ").strip().split()
        if len(first) != 2:
            raise ValueError("Enter N and M on the first line.")
        n, m = map(int, first)
        second = input("Enter K C: ").strip().split()
        if len(second) != 2:
            raise ValueError("Enter K and C on the second line.")
        k, c = map(int, second)
        if n < 1 or m < 0 or k < 0 or c < 0:
            raise ValueError("N must be at least 1; M, K, and C must be non-negative.")

        flights = []
        print("Enter each flight as: source destination price")
        for i in range(m):
            parts = input().strip().split()
            if len(parts) != 3:
                raise ValueError(f"Flight {i + 1} must contain source destination price.")
            u, v, price = map(int, parts)
            if not (1 <= u <= n and 1 <= v <= n):
                raise ValueError(f"Flight endpoints must be between 1 and {n}.")
            if price < 0:
                raise ValueError("Ticket prices must be non-negative.")
            flights.append((u, v, price))

        min_cost, route_steps = find_route(n, flights, k, c)
        if min_cost is None:
            print("\nMinimum Cost: -1")
            print("Route: No valid route within the stop limit.")
        else:
            print(f"\nMinimum Cost: {min_cost}")
            if not route_steps:
                print("Route: 1 (already at destination)")
            else:
                route = str(route_steps[0]["source"])
                for step in route_steps:
                    if step["coupon"]:
                        route += f' --[{step["price"]} -> {step["final_price"]}, COUPON]--> {step["destination"]}'
                    else:
                        route += f' --[{step["price"]}]--> {step["destination"]}'
                print("Route: " + route)
            print("\nFlight Details:")
            print("From  To  Original  Final  Coupon")
            for step in route_steps:
                print(f'{step["source"]:>4} {step["destination"]:>3} {step["price"]:>8} {step["final_price"]:>6} {"Yes" if step["coupon"] else "No"}')

        write_csv(flights, route_steps)
        build_svg(n, flights, route_steps, min_cost, c)
        print(f"\nCSV saved: {os.path.abspath(CSV_FILE)}")
        print(f"Graph saved: {os.path.abspath(SVG_FILE)}")
        print("Open the SVG in Chrome and click Play to animate the journey.")
    except (ValueError, EOFError) as error:
        print(f"Input error: {error}")


if __name__ == "__main__":
    main()
