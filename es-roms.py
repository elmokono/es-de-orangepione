#!/usr/bin/env python3

import os
import json
import xml.etree.ElementTree as ET

ROMS_DIR = "/home/daniel/roms"
ES_DIR = "/home/daniel/.emulationstation"
CACHE_FILE = os.path.expanduser("~/.cache/es_cache.json")
DAT_DIR = "/home/daniel/roms/dats"
CORES_DIR = os.path.expanduser("~/.config/retroarch/cores")

# ---------- ICONOS ----------
OK = "✔"
NEW = "🆕"
CACHE = "⚡"
SKIP = "⏭"
SYS = "🎮"
WARN = "⚠"
CORE = "🎯"

# ---------- CACHE ----------
if os.path.exists(CACHE_FILE):
    cache = json.load(open(CACHE_FILE))
    print(f"{CACHE} Cache cargado ({len(cache)} entradas)")
else:
    cache = {}
    print(f"{WARN} Cache nuevo")

# ---------- CORES ----------
def detect_cores():
    cores = {}
    if not os.path.exists(CORES_DIR):
        return cores

    for f in os.listdir(CORES_DIR):
        if f.endswith("_libretro.so"):
            name = f.replace("_libretro.so", "")
            cores[name] = os.path.join(CORES_DIR, f)

    return cores

cores = detect_cores()

# ---------- CORE SELECTION ----------
def pick_core(system):
    priorities = {
        "arcade": ["fbneo"],
        "nes": ["nestopia", "fceumm"],
        "snes": ["snes9x2002"],
        "gba": ["mgba", "gpsp"],
        "gb": ["gambatte"],
        "gbc": ["gambatte"],
        "genesis": ["genesis_plus_gx", "picodrive"],
        "megadrive": ["genesis_plus_gx", "picodrive"],
        "psx": ["pcsx_rearmed"],
        "c64": ["vice_x64"],
        "scummvm": ["scummvm"],
        "mame": ["mame2003"]
    }

    if system not in priorities:
        return None

    for core in priorities[system]:
        if core in cores:
            return cores[core]

    return None

# ---------- LOAD DAT ----------
def load_dat(system):
    path = os.path.join(DAT_DIR, f"{system}.dat")

    if not os.path.exists(path):
        print(f"  {WARN} No DAT para {system}")
        return {}, set()

    tree = ET.parse(path)
    root = tree.getroot()

    mapping = {}
    clones = set()

    for game in root.findall("game"):
        name = game.attrib.get("name")
        desc = game.find("description")

        if not name or desc is None:
            continue

        mapping[name] = desc.text

        if "cloneof" in game.attrib:
            clones.add(name)

    return mapping, clones

# ---------- MAIN ----------
systems_xml = []

for system in sorted(os.listdir(ROMS_DIR)):
    system_path = os.path.join(ROMS_DIR, system)

    if not os.path.isdir(system_path):
        continue

    print(f"\n{SYS} {system.upper()}")

    dat, clones = load_dat(system)
    core_path = pick_core(system)

    if core_path:
        print(f"  {CORE} Core: {os.path.basename(core_path)}")
    else:
        print(f"  {WARN} Sin core asignado")

    gamelist = []
    seen = set()

    total = 0
    new_count = 0
    cache_count = 0
    dup_count = 0

    for file in sorted(os.listdir(system_path)):
        if not file.lower().endswith((".zip", ".nes", ".sfc", ".smc", ".gba", ".gb", ".gbc")):
            continue

        total += 1

        full = os.path.join(system_path, file)
        short = os.path.splitext(file)[0]

        stat = os.stat(full)
        key = f"{file}-{stat.st_size}-{int(stat.st_mtime)}"

        if key in cache:
            name = cache[key]
            cache_count += 1
            icon = CACHE
        else:
            if short in dat:
                if short in clones:
                    print(f"  {SKIP} clone: {file}")
                    continue
                name = dat[short]
            else:
                name = short

            cache[key] = name
            new_count += 1
            icon = NEW

        if name in seen:
            dup_count += 1
            print(f"  ⏭ dup: {name}")
            continue

        seen.add(name)
        gamelist.append((file, name))

        print(f"  {icon} {file} → {name}")

    # ---------- WRITE GAMELIST ----------
    gl_dir = os.path.join(ES_DIR, "gamelists", system)
    os.makedirs(gl_dir, exist_ok=True)

    with open(os.path.join(gl_dir, "gamelist.xml"), "w") as f:
        f.write("<gameList>\n")
        for rom, name in gamelist:
            f.write(f"""
  <game>
    <path>./{rom}</path>
    <name>{name}</name>
  </game>
""")
        f.write("</gameList>")

    print(f"  {OK} {len(gamelist)} juegos únicos")
    print(f"  📊 total:{total} new:{new_count} cache:{cache_count} dup:{dup_count}")

    # ---------- COMMAND ----------
    if core_path:
        command = f"retroarch -L {core_path} %ROM%"
    else:
        command = "retroarch %ROM%"

    # ---------- SYSTEM CONFIG ----------
    systems_xml.append(f"""
  <system>
    <name>{system}</name>
    <fullname>{system.upper()}</fullname>
    <path>{system_path}</path>
    <extension>.zip .nes .sfc .smc .gba .gb .gbc</extension>
    <command>{command}</command>
    <platform>{system}</platform>
    <theme>{system}</theme>
  </system>
""")

# ---------- WRITE ES CONFIG ----------
with open(os.path.join(ES_DIR, "es_systems.cfg"), "w") as f:
    f.write("<systemList>\n")
    for s in systems_xml:
        f.write(s)
    f.write("\n</systemList>")

# ---------- SAVE CACHE ----------
os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
json.dump(cache, open(CACHE_FILE, "w"), indent=2)

print(f"\n{OK} DONE")
print(f"{CACHE} Cache guardado ({len(cache)} entradas)")
