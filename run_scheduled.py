"""Scheduled runner: refresh WASP data, build reports from saved presets, email them with one email per recipient group.

Usage:
    python run_scheduled.py                       # run every group in schedule.json
    python run_scheduled.py --only "Preset name"  # run one preset
    python run_scheduled.py --skip-refresh        # reuse the data already in Postgres
    python run_scheduled.py --dry-run             # build reports but don't send email

Optional .env settings:
    REPORT_DIR          where reports are saved (default Documents/WASP Assembly Reports)
    ALERT_EMAIL         who gets an email if something fails
    MAX_DATA_AGE_HOURS  warn in the email if data is older than this (default 36)
    MAIL_BACKEND        outlook (default) or smtp, see emailer.py
"""
import argparse
import json
import logging
import os
import sys
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import assembly  # noqa: E402
import item  # noqa: E402
import location  # noqa: E402
import presets  # noqa: E402
import report_gen  # noqa: E402
import settings  # noqa: E402
from emailer import send_email  # noqa: E402

# keep in sync with report_gen.build_report_query's contract_map
CONTRACTS = ["RGI35", "QIN05", "QIN11", "General Stock", "All"]

BASE_DIR = Path(__file__).resolve().parent
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(BASE_DIR / "run_scheduled.log"), logging.StreamHandler()],
)
log = logging.getLogger("scheduled")


def refresh_data():
    """Pull everything from WASP into Postgres. Must match what the UI's refresh does."""
    item.inventory_to_database(item.entire_inventory_api_call())
    location.update_location_table()
    assembly.update_bom_table()
    settings.save_refresh_timestamp()


def buildable_line(path):
    """Pull the 'Buildable Units: N' line off the report's title page for the email body."""
    try:
        from openpyxl import load_workbook

        wb = load_workbook(path)
        return wb["Title Page"]["A4"].value
    except Exception:
        return None


def run_job(name, output_dir):
    """Build one report and return what the email needs. Does not send anything."""
    preset = next((p for p in presets.load_presets() if p["name"] == name), None)
    if preset is None:
        raise ValueError("Preset not found: " + name)

    path = report_gen.create_report(
        assembly_num=preset["assembly_id"].split(" - ")[0],  # stored as "X61612 - description"
        contract=preset["contract"],
        output_directory=output_dir,
        include_inspection=preset["include_inspection"],
        include_on_order=preset["include_on_order"],
        include_kitted=preset["include_kitted"],
        include_cost=preset["include_cost"],
        include_assembled=preset["include_assembled"],
        desired_amount=preset["desired_amount"],
        list_of_contracts=CONTRACTS,
        preset_name=name,
    )
    log.info("Built report: %s", path)
    return {"name": name, "path": path, "summary": buildable_line(path)}


def data_freshness_line():
    ts = settings.database_refresh_timestamp()
    if ts is None:
        return "Data as of: unknown"
    line = "Data as of: " + ts.strftime("%Y-%m-%d %H:%M")
    max_age = timedelta(hours=float(os.getenv("MAX_DATA_AGE_HOURS", 36)))
    if datetime.now(timezone.utc) - ts.astimezone(timezone.utc) > max_age:
        line += "  (WARNING: this data is older than expected, quantities may be out of date)"
    return line


def send_group_email(group, results, failed_names, dry_run=False):
    recipients = group["recipients"]
    lines = ["WASP build reports (" + str(len(results)) + " attached)", ""]
    for r in results:
        lines.append("- " + r["name"] + (": " + str(r["summary"]) if r["summary"] else ""))
    lines += ["", data_freshness_line()]
    if failed_names:
        lines += ["", "WARNING: these reports could not be generated:"]
        lines += ["- " + n for n in failed_names]
    lines += ["", "(Automated message)"]
    body = "\n".join(lines)
    label = group.get("name", "WASP Build Reports")
    subject = label + " - " + datetime.now().strftime("%Y-%m-%d")
    paths = [r["path"] for r in results]

    if dry_run:
        log.info("Dry run, not sending. Would email %s with %d attachment(s):\n%s", recipients, len(paths), body)
    else:
        send_email(recipients, subject, body, paths)
        log.info("Emailed %d report(s) to %s", len(paths), recipients)


def alert(message):
    """Best-effort failure notice so a broken nightly job doesn't go unnoticed."""
    to = os.getenv("ALERT_EMAIL")
    if not to:
        return
    try:
        send_email([to], "WASP report job FAILED", message)
    except Exception:
        log.exception("Could not send alert email")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(BASE_DIR / "schedule.json"))
    parser.add_argument("--only", help="run just this preset name (in every group that lists it)")
    parser.add_argument("--skip-refresh", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    with open(args.config) as f:
        groups = json.load(f)["groups"]

    # drop groups with no recipients, and apply --only
    groups = [g for g in groups if g.get("recipients") or args.dry_run]
    if args.only:
        groups = [dict(g, presets=[p for p in g["presets"] if p == args.only]) for g in groups]
        groups = [g for g in groups if g["presets"]]
    if not groups:
        log.error("No groups to run in %s (check recipients and --only)", args.config)
        return 1

    output_dir = os.getenv("REPORT_DIR") or str(Path.home() / "Documents" / "WASP Assembly Reports")
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    if not args.skip_refresh:
        try:
            log.info("Refreshing data from WASP...")
            refresh_data()
        except Exception:
            err = traceback.format_exc()
            log.error("Refresh failed, not sending reports:\n%s", err)
            alert("Data refresh failed, so no reports were sent.\n\n" + err)
            return 1

    # build each distinct preset once, even if several groups use it
    built, failed = {}, set()
    for name in dict.fromkeys(p for g in groups for p in g["presets"]):
        try:
            built[name] = run_job(name, output_dir)
        except Exception:
            failed.add(name)
            err = traceback.format_exc()
            log.error("Report failed: %s\n%s", name, err)
            alert("Report job failed: " + name + "\n\n" + err)

    # one email per group, with only that group's attachments
    problems = len(failed)
    for g in groups:
        results = [built[n] for n in g["presets"] if n in built]
        failed_names = [n for n in g["presets"] if n in failed]
        if not results:
            log.error("Nothing to send to %s", g.get("recipients"))
            continue
        try:
            send_group_email(g, results, failed_names, dry_run=args.dry_run)
        except Exception:
            problems += 1
            err = traceback.format_exc()
            log.error("Sending email failed for %s:\n%s", g.get("recipients"), err)
            alert("Reports were built but the email failed to send to " + str(g.get("recipients")) + "\n\n" + err)

    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
