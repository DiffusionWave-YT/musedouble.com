"""Check the actual CSS role pairs in both themes against the project's thresholds."""
from pathlib import Path
import re
import json

root=Path(__file__).resolve().parents[1]
css=(root/"web/app/style.css").read_text()


def luminance(value):
    rgb=[int(value[i:i+2],16)/255 for i in (1,3,5)]
    linear=[x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in rgb]
    return sum(x*w for x,w in zip(linear,[.2126,.7152,.0722]))


results=[]
for name,selector in [("light",r":root\{([^}]+)\}"),("dark",r':root\[data-theme=dark\]\{([^}]+)\}')]:
    tokens=dict(re.findall(r"--([a-z-]+):(#\w{6})",re.search(selector,css).group(1)))
    pairs=[(fg,bg,4.5) for fg in ["text","muted","accent","error"] for bg in ["bg","surface","raised","selected"]]
    pairs += [("on-accent","accent",4.5),("success","raised",4.5),("control","surface",3),("muted","raised",3)]
    for fg,bg,minimum in pairs:
        a,b=sorted([luminance(tokens[fg]),luminance(tokens[bg])])
        ratio=(b+.05)/(a+.05)
        results.append({"theme":name,"foreground":fg,"background":bg,"ratio":round(ratio,2),"minimum":minimum,"passed":ratio>=minimum})
dest=root/"storage/contrast.json";dest.parent.mkdir(exist_ok=True,parents=True);dest.write_text(json.dumps(results,indent=2),encoding="utf-8")
failed=[r for r in results if not r["passed"]]
print(json.dumps({"pairs":len(results),"failures":failed}))
raise SystemExit(bool(failed))
