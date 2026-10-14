import java.util.*;
import java.awt.*;
import javax.swing.*;

public class ClosestPairAnalysis {

    static class Point {
        double x, y;
        int id;

        Point(double x, double y, int id) {
            this.x = x;
            this.y = y;
            this.id = id;
        }

        public String toString() {
            return String.format("(%.2f, %.2f)", x, y);
        }
    }

    static class Pair {
        Point a, b;
        double d;

        Pair(Point a, Point b) {
            this.a = a;
            this.b = b;
            d = Math.hypot(a.x - b.x, a.y - b.y);
        }
    }


    static double distance(Point a, Point b) {
        return Math.hypot(a.x - b.x, a.y - b.y);
    }

    static Pair brute(Point[] p) {
        Pair best = null;

        for (int i = 0; i < p.length; i++) {
            for (int j = i + 1; j < p.length; j++) {
                Pair current = new Pair(p[i], p[j]);

                if (best == null || current.d < best.d)
                    best = current;
            }
        }

        return best;
    }


    static Pair divide(Point[] points) {
        Point[] px = points.clone();
        Point[] py = points.clone();

        Arrays.sort(px, Comparator.comparingDouble(p -> p.x));
        Arrays.sort(py, Comparator.comparingDouble(p -> p.y));

        return solve(px, py);
    }

    static Pair solve(Point[] px, Point[] py) {
        int n = px.length;

        if (n <= 3)
            return brute(px);

        int mid = n / 2;
        double midX = px[mid].x;

        Point[] leftX = Arrays.copyOfRange(px, 0, mid);
        Point[] rightX = Arrays.copyOfRange(px, mid, n);

        Set<Integer> leftIds = new HashSet<>();
        for (Point p : leftX)
            leftIds.add(p.id);

        ArrayList<Point> leftY = new ArrayList<>();
        ArrayList<Point> rightY = new ArrayList<>();

        for (Point p : py) {
            if (leftIds.contains(p.id))
                leftY.add(p);
            else
                rightY.add(p);
        }

        Pair left = solve(leftX, leftY.toArray(new Point[0]));
        Pair right = solve(rightX, rightY.toArray(new Point[0]));

        Pair best = left.d <= right.d ? left : right;

        ArrayList<Point> strip = new ArrayList<>();

        for (Point p : py) {
            if (Math.abs(p.x - midX) < best.d)
                strip.add(p);
        }

        for (int i = 0; i < strip.size(); i++) {
            for (int j = i + 1; j < strip.size(); j++) {
                if (strip.get(j).y - strip.get(i).y >= best.d)
                    break;

                Pair current = new Pair(strip.get(i), strip.get(j));

                if (current.d < best.d)
                    best = current;
            }
        }

        return best;
    }


    static class Result {
        int n;
        double bruteTime, divideTime;

        Result(int n, double b, double d) {
            this.n = n;
            bruteTime = b;
            divideTime = d;
        }
    }

    static double timeBrute(Point[] p) {
        long start = System.nanoTime();
        brute(p);
        return (System.nanoTime() - start) / 1e6;
    }

    static double timeDivide(Point[] p) {
        long start = System.nanoTime();
        divide(p);
        return (System.nanoTime() - start) / 1e6;
    }

    static ArrayList<Result> benchmark() {
        int[] sizes = {100, 250, 500, 1000, 2000, 3000};
        ArrayList<Result> results = new ArrayList<>();
        Random r = new Random(42);

        System.out.println("\n--- Performance Comparison ---");
        System.out.printf("%-10s %-18s %-18s%n",
                "N", "Brute Force(ms)", "Divide & Conquer(ms)");

        for (int n : sizes) {
            Point[] p = new Point[n];

            for (int i = 0; i < n; i++)
                p[i] = new Point(r.nextDouble() * 1000,
                                 r.nextDouble() * 1000, i);

            brute(Arrays.copyOf(p, Math.min(n, 100)));
            divide(Arrays.copyOf(p, Math.min(n, 100)));

            double b = 0, d = 0;

            for (int i = 0; i < 3; i++) {
                b += timeBrute(p);
                d += timeDivide(p);
            }

            b /= 3;
            d /= 3;

            results.add(new Result(n, b, d));

            System.out.printf("%-10d %-18.6f %-18.6f%n", n, b, d);
        }

        return results;
    }

    static class MazeGraph extends JPanel {
        Point[] points;
        Pair brute, divide;
        double midX, stripWidth;

        MazeGraph(Point[] p, Pair b, Pair d) {
            points = p;
            brute = b;
            divide = d;

            Point[] sorted = p.clone();
            Arrays.sort(sorted, Comparator.comparingDouble(a -> a.x));

            midX = sorted[sorted.length / 2].x;

            Pair left = brute(Arrays.copyOfRange(
                    sorted, 0, sorted.length / 2));
            Pair right = brute(Arrays.copyOfRange(
                    sorted, sorted.length / 2, sorted.length));

            stripWidth = Math.min(left.d, right.d);

            setPreferredSize(new Dimension(850, 500));
            setBackground(Color.WHITE);
        }

        protected void paintComponent(Graphics g) {
            super.paintComponent(g);

            int w = getWidth(), h = getHeight();
            int margin = 50;

            double minX = points[0].x, maxX = points[0].x;
            double minY = points[0].y, maxY = points[0].y;

            for (Point p : points) {
                minX = Math.min(minX, p.x);
                maxX = Math.max(maxX, p.x);
                minY = Math.min(minY, p.y);
                maxY = Math.max(maxY, p.y);
            }

            if (minX == maxX) { minX--; maxX++; }
            if (minY == maxY) { minY--; maxY++; }

            double px = (maxX - minX) * 0.08;
            double py = (maxY - minY) * 0.08;
            minX -= px; maxX += px;
            minY -= py; maxY += py;

            final double x0 = minX, x1 = maxX;
            final double y0 = minY, y1 = maxY;

            int pw = w - 2 * margin, ph = h - 2 * margin;

            java.util.function.ToIntFunction<Double> sx =
                    x -> margin + (int)((x - x0) / (x1 - x0) * pw);

            java.util.function.ToIntFunction<Double> sy =
                    y -> h - margin - (int)((y - y0) / (y1 - y0) * ph);

     
            int xLeft = sx.applyAsInt(midX - stripWidth);
            int xRight = sx.applyAsInt(midX + stripWidth);

            g.setColor(new Color(255, 165, 0, 55));
            g.fillRect(xLeft, margin, xRight - xLeft, ph);

            g.setColor(Color.GRAY);
            g.drawLine(sx.applyAsInt(midX), margin,
                       sx.applyAsInt(midX), h - margin);

            for (Point p : points) {
                g.setColor(Color.BLACK);
                g.fillOval(sx.applyAsInt(p.x) - 4,
                           sy.applyAsInt(p.y) - 4, 8, 8);
            }

            drawPair(g, brute, Color.RED, sx, sy);
            drawPair(g, divide, Color.BLUE, sx, sy);

            g.setColor(Color.RED);
            g.drawString("Red: Brute Force", 20, 20);
            g.setColor(Color.BLUE);
            g.drawString("Blue: Divide & Conquer", 160, 20);
            g.setColor(Color.GRAY);
            g.drawString("Vertical line: Division", 360, 20);
            g.setColor(Color.ORANGE);
            g.drawString("Orange: Strip", 560, 20);
        }

        void drawPair(Graphics g, Pair p, Color c,
                      java.util.function.ToIntFunction<Double> sx,
                      java.util.function.ToIntFunction<Double> sy) {
            g.setColor(c);
            g.drawLine(sx.applyAsInt(p.a.x), sy.applyAsInt(p.a.y),
                       sx.applyAsInt(p.b.x), sy.applyAsInt(p.b.y));
        }
    }

    static class TimeGraph extends JPanel {
        ArrayList<Result> results;

        TimeGraph(ArrayList<Result> results) {
            this.results = results;
            setPreferredSize(new Dimension(850, 350));
            setBackground(Color.WHITE);
        }

        protected void paintComponent(Graphics g) {
            super.paintComponent(g);

            int w = getWidth(), h = getHeight();
            int left = 65, right = 30, top = 45, bottom = 50;

            int gw = w - left - right, gh = h - top - bottom;

            double maxTime = 0;
            int maxN = 1;

            for (Result r : results) {
                maxTime = Math.max(maxTime,
                        Math.max(r.bruteTime, r.divideTime));
                maxN = Math.max(maxN, r.n);
            }

            if (maxTime == 0) maxTime = 1;

            g.setColor(Color.BLACK);
            g.drawLine(left, h - bottom, w - right, h - bottom);
            g.drawLine(left, top, left, h - bottom);
            g.drawString("Execution Time vs Number of Points", w / 2 - 120, 20);
            g.drawString("Number of points (N)", w / 2 - 65, h - 10);
            g.drawString("Time (ms)", 5, top);

            int bx = -1, by = -1, dx = -1, dy = -1;

            for (Result r : results) {
                int x = left + (int)((double)r.n / maxN * gw);
                int yB = h - bottom - (int)(r.bruteTime / maxTime * gh);
                int yD = h - bottom - (int)(r.divideTime / maxTime * gh);

                g.setColor(Color.RED);
                if (bx != -1) g.drawLine(bx, by, x, yB);
                g.fillOval(x - 4, yB - 4, 8, 8);

                g.setColor(Color.BLUE);
                if (dx != -1) g.drawLine(dx, dy, x, yD);
                g.fillOval(x - 4, yD - 4, 8, 8);

                g.setColor(Color.BLACK);
                g.drawString(String.valueOf(r.n), x - 10, h - bottom + 18);

                bx = dx = x;
                by = yB;
                dy = yD;
            }

            g.setColor(Color.RED);
            g.drawString("Red: Brute Force", w - 230, 25);
            g.setColor(Color.BLUE);
            g.drawString("Blue: Divide & Conquer", w - 115, 25);
        }
    }

   
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        Random random = new Random();

        System.out.print("Enter number of points: ");
        int n = sc.nextInt();

        if (n < 2) {
            System.out.println("At least 2 points are required.");
            sc.close();
            return;
        }

        Point[] points = new Point[n];

        for (int i = 0; i < n; i++)
            points[i] = new Point(random.nextDouble() * 100,
                                  random.nextDouble() * 100, i);

        long start = System.nanoTime();
        Pair b = brute(points);
        double tb = (System.nanoTime() - start) / 1e6;

        start = System.nanoTime();
        Pair d = divide(points);
        double td = (System.nanoTime() - start) / 1e6;

        System.out.println("\n--- Brute Force ---");
        System.out.printf("Distance: %.6f%n", b.d);
        System.out.println("Points: " + b.a + " and " + b.b);
        System.out.printf("Time: %.6f ms%n", tb);

        System.out.println("\n--- Divide and Conquer ---");
        System.out.printf("Distance: %.6f%n", d.d);
        System.out.println("Points: " + d.a + " and " + d.b);
        System.out.printf("Time: %.6f ms%n", td);

        System.out.println("\nVerification: " +
                (Math.abs(b.d - d.d) < 1e-9
                 ? "Both algorithms agree."
                 : "Results differ!"));

        ArrayList<Result> results = benchmark();
        sc.close();

        SwingUtilities.invokeLater(() -> {
            JFrame frame = new JFrame("Closest Pair Analysis");

            JSplitPane split = new JSplitPane(
                    JSplitPane.VERTICAL_SPLIT,
                    new JScrollPane(new MazeGraph(points, b, d)),
                    new JScrollPane(new TimeGraph(results)));

            split.setResizeWeight(0.65);
            frame.add(split);
            frame.setSize(1000, 900);
            frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
            frame.setLocationRelativeTo(null);
            frame.setVisible(true);
        });
    }
}