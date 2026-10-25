"""printloop: ideate -> design -> slice -> print -> refine for the Bambu H2S.

  printloop new NAME            start a design from the template
  printloop photo NAME FILE...  add reference (ideate) or result (print) photos
  printloop build NAME          run part.py, export STEP/STL, check printability, render preview
  printloop slice NAME          slice with the Bambu Studio CLI (run on the machine with Bambu Studio)
  printloop print NAME          open the sliced file in Bambu Studio to send to the H2S
  printloop log NAME ...        record how a print came out
  printloop status [NAME]       show where each design is in the loop
  printloop profiles            flatten Bambu Studio presets into printer/profiles/
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys

import yaml

from . import config


def cmd_new(args):
    target = config.DESIGNS / args.name
    if target.exists():
        raise SystemExit(f"{target.relative_to(config.ROOT)} already exists")
    shutil.copytree(config.TEMPLATE, target)
    for path in target.rglob("*"):
        if path.is_file():
            path.write_text(path.read_text().replace("{{name}}", args.name))
    print(f"Created {target.relative_to(config.ROOT)}: fill in brief.md, then part.py")


def cmd_photo(args):
    from pathlib import Path
    from .photos import add_photo
    for source in args.files:
        entry = add_photo(args.name, Path(source), args.kind, args.caption or "", args.revision)
        print(f"designs/{args.name}/{entry['file']}  {entry['size_px'][0]}x{entry['size_px'][1]}  {entry['caption']}")


def cmd_build(args):
    from .build import build
    overrides = {}
    for item in args.set or []:
        key, _, value = item.partition("=")
        overrides[key] = yaml.safe_load(value)
    report = build(args.name, overrides, preview=not args.no_preview)
    out = (config.DESIGNS / args.name / "out").relative_to(config.ROOT)
    print((config.DESIGNS / args.name / "out" / "report.md").read_text())
    print(f"Outputs in {out}/")
    if report["status"] == "fail":
        sys.exit(1)


def cmd_slice(args):
    from .slicer import slice_design
    result = slice_design(args.name, args.profile, args.extra)
    for plate in result["plates"]:
        print(f"plate {plate['index']}: {plate['time']}, {plate['weight_g']:.1f} g")
    print(f"Sliced -> designs/{args.name}/out/{result['file']}")


def cmd_print(args):
    from .slicer import open_in_bambu_studio
    out = config.DESIGNS / args.name / "out"
    files = sorted(out.glob("*.gcode.3mf"), key=lambda p: p.stat().st_mtime)
    if not files:
        raise SystemExit(f"Nothing sliced yet: printloop slice {args.name}")
    open_in_bambu_studio(files[-1])
    print(f"Opened {files[-1].name}. In Bambu Studio press Print plate and pick the H2S, "
          f"then record the result with: printloop log {args.name} --result ...")


def cmd_log(args):
    from .log import add_entry, read_log
    if not args.result:
        print(yaml.safe_dump(read_log(args.name), sort_keys=False, allow_unicode=True) or "No prints logged yet.")
        return
    entry = add_entry(args.name, args.result, args.measure or [], args.issue or [], args.next or [],
                      args.notes, args.photo or [], args.revision)
    print(yaml.safe_dump([entry], sort_keys=False, allow_unicode=True))


def cmd_status(args):
    from .log import read_log
    names = [args.name] if args.name else sorted(
        p.name for p in config.DESIGNS.iterdir() if (p / "part.py").exists() and p.name != "_template")
    for name in names:
        module = config.load_part_module(name)
        out = config.DESIGNS / name / "out"
        report = json.loads((out / "report.json").read_text()) if (out / "report.json").exists() else None
        sliced = sorted(out.glob(f"{config.stem(name, module.REVISION)}*.gcode.3mf")) if out.exists() else []
        log = read_log(name)
        last = log[-1] if log else None
        built = f"built r{report['revision']} ({report['status']})" if report else "not built"
        print(f"{name}: r{module.REVISION}, {built}, {'sliced' if sliced else 'not sliced'}, "
              f"{len(log)} print(s) logged" + (f", last r{last['revision']} {last['result']}" if last else ""))


def cmd_profiles(args):
    from pathlib import Path
    from .profiles import write_profiles
    dirs = [Path(d) for d in args.dirs] if args.dirs else None
    for path in write_profiles(dirs):
        data = json.loads(path.read_text())
        print(f"{path.relative_to(config.ROOT)}: {data['name']} ({len(data)} settings)")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="printloop", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("new", help="start a design from the template")
    p.add_argument("name")
    p.set_defaults(func=cmd_new)

    p = sub.add_parser("photo", help="add photos to a design")
    p.add_argument("name")
    p.add_argument("files", nargs="+")
    p.add_argument("--kind", choices=["ref", "print"], default="ref",
                   help="ref: reference shots for ideation (default); print: how a print came out")
    p.add_argument("--caption", help="what the photo shows, e.g. 'shelf bracket, side view with ruler'")
    p.add_argument("--revision", type=int, help="for print photos; defaults to the current REVISION")
    p.set_defaults(func=cmd_photo)

    p = sub.add_parser("build", help="export, check and preview a design")
    p.add_argument("name")
    p.add_argument("--set", action="append", metavar="KEY=VALUE", help="override a parameter for this build")
    p.add_argument("--no-preview", action="store_true")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("slice", help="slice with the Bambu Studio CLI")
    p.add_argument("name")
    p.add_argument("--profile", help="variant from printer/slicer.yaml, e.g. strong or petg")
    p.add_argument("--extra", nargs=argparse.REMAINDER, help="extra Bambu Studio CLI args, e.g. --curr-bed-type=...")
    p.set_defaults(func=cmd_slice)

    p = sub.add_parser("print", help="open the latest sliced file in Bambu Studio")
    p.add_argument("name")
    p.set_defaults(func=cmd_print)

    p = sub.add_parser("log", help="record a print result, or show the log")
    p.add_argument("name")
    p.add_argument("--result", choices=["success", "partial", "fail"])
    p.add_argument("--revision", type=int, help="defaults to the current REVISION in part.py")
    p.add_argument("--measure", action="append", metavar="FEATURE=EXPECTED:MEASURED")
    p.add_argument("--issue", action="append")
    p.add_argument("--next", action="append", help="a change to make in the next revision")
    p.add_argument("--photo", action="append", help="path to a photo, ideally under designs/NAME/photos/")
    p.add_argument("--notes")
    p.set_defaults(func=cmd_log)

    p = sub.add_parser("status", help="where each design is in the loop")
    p.add_argument("name", nargs="?")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("profiles", help="flatten Bambu Studio presets for the CLI")
    p.add_argument("--dirs", nargs="+", help="search these preset folders instead of the defaults")
    p.set_defaults(func=cmd_profiles)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
