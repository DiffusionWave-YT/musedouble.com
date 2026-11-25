from pathlib import Path
import json
import re

root = Path(__file__).resolve().parents[1]
css = (root / "web/app/style.css").read_text(encoding="utf-8")


def rgb(value):
    return [int(value[i:i + 2], 16) for i in (1, 3, 5)]


def luminance(channels):
    linear = [x / 255 / 12.92 if x / 255 <= .04045 else ((x / 255 + .055) / 1.055) ** 2.4 for x in channels]
    return sum(x * w for x, w in zip(linear, [.2126, .7152, .0722]))


def ratio(foreground, background):
    low, high = sorted([luminance(foreground), luminance(background)])
    return (high + .05) / (low + .05)


def mix(color, base, alpha):
    return [round(c * alpha + b * (1 - alpha)) for c, b in zip(color, base)]


themes = {
    "light": (r":root\s*\{([^}]+)\}", .18, "t6"),
    "dark": (r":root\[data-theme=dark\]\s*\{([^}]+)\}", .28, "t2"),
}
tones = {name: {"t4": a, "t6": b, "t2": c} for name, a, b, c in
         re.findall(r"\.ic-tono-(\w+)\s*\{\s*--t4:\s*(#\w{6});\s*--t6:\s*(#\w{6});\s*--t2:\s*(#\w{6})", css)}

results = []
for name, (selector, alpha, tone_key) in themes.items():
    tokens = {k: rgb(v) for k, v in re.findall(r"--([a-z-]+):\s*(#\w{6})", re.search(selector, css).group(1))}
    pairs = [(fg, bg, 4.5) for fg in ["text", "muted", "accent", "error"] for bg in ["bg", "surface", "raised", "selected"]]
    pairs += [("on-accent", "accent", 4.5), ("success", "raised", 4.5), ("success", "surface", 4.5),
              ("control", "surface", 3), ("muted", "raised", 3), ("bg", "text", 4.5), ("bg", "error", 4.5), ("accent", "surface", 3)]
    for fg, bg, minimum in pairs:
        value = ratio(tokens[fg], tokens[bg])
        results.append({"theme": name, "foreground": fg, "background": bg, "ratio": round(value, 2), "minimum": minimum, "passed": value >= minimum})
    for tone, colors in tones.items():
        tile = mix(rgb(colors["t4"]), tokens["surface"], alpha)
        value = ratio(rgb(colors[tone_key]), tile)
        results.append({"theme": name, "foreground": "icon-" + tone, "background": "tile", "ratio": round(value, 2), "minimum": 3, "passed": value >= 3})

destination = root / "storage/contrast.json"
destination.parent.mkdir(exist_ok=True, parents=True)
destination.write_text(json.dumps(results, indent=2), encoding="utf-8")
failed = [r for r in results if not r["passed"]]
print(json.dumps({"pairs": len(results), "failures": failed}))
raise SystemExit(bool(failed))
