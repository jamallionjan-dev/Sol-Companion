from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[3] / "05_TOOLS" / "sol_drive_sim" / "analyze_heli_flight.py"
spec = importlib.util.spec_from_file_location("analyze_heli_flight", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)

sample = """ms,vehicle_id,script,seat,controls,x,y,world_altitude_z,ground_z,raw_agl,skid_agl,skid_agl_method,vertical_z_per_s,kmh,forward_x,forward_y
1000,1,Base.UH1BHuey,0,W=true;S=false;A=false;D=false;UP=false;DOWN=false;LEFT=false;RIGHT=false,10,20,0.50,0.40,-0.10,0.00,AviationCore,,0,1,0
1100,1,Base.UH1BHuey,0,W=true;S=false;A=false;D=false;UP=false;DOWN=false;LEFT=false;RIGHT=false,10.2,20.1,1.50,0.40,0.90,0.90,AviationCore,10,0,1,0
1200,1,Base.UH1BHuey,0,W=false;S=false;A=true;D=false;UP=true;DOWN=false;LEFT=false;RIGHT=false,11,21,2.00,0.40,1.40,0.50,AviationCore,5,15,0.8,0.2
1300,1,Base.UH1BHuey,0,W=false;S=true;A=false;D=false;UP=false;DOWN=false;LEFT=false;RIGHT=false,12,22,1.00,0.40,0.40,-0.50,AviationCore,-10,0,0.8,0.2
"""

with tempfile.TemporaryDirectory() as temporary:
    source = Path(temporary) / "flight.txt"
    source.write_text(sample, encoding="utf-8")
    output = module.summarize(source)
    assert "Samples: 4" in output
    assert "Duration: 0.3s" in output
    assert "World altitude Z: 0.50 -> 1.00; range 0.50..2.00" in output
    assert "Corrected skid AGL: 0.00 -> -0.50; range -0.50..0.90" in output
    assert "Horizontal displacement: dx=2.00, dy=2.00" in output
    assert "0.0s + 0.1s: W" in output
    assert "0.2s + 0.0s: A+UP" in output
    assert "0.3s + 0.0s: S" in output
    assert "calibrate before changing Sol's controller" in output

print("s129 flight analyzer PASS: input episodes, world altitude/AGL, displacement, vertical rate and cautious interpretation")
