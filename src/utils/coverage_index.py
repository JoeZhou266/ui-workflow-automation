from __future__ import annotations

import glob
import os
from collections import defaultdict
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Optional

import coverage
from coverage.files import flat_rootname


def build_custom_index(
    coverage_dir: str = "reports/coverage",
    data_file: str = ".coverage",
    _cov_factory=None,
) -> str:
    """Read .coverage binary and return HTML for reports/coverage/custom_index.html.

    Uses coverage Python API (D-14). Accepts _cov_factory for unit-test injection:
    callable(data_file) -> Coverage-like object; defaults to coverage.Coverage.

    WARNING: Uses coverage._analyze() which is an internal API. Stable across
    coverage.py 5.x-7.x but may break in a future major version. Wrapped in
    try/except at the call site (pytest_sessionfinish) to fail-open.

    Args:
        coverage_dir: Directory containing coverage HTML output (for CSS discovery
                      and output). Default: "reports/coverage".
        data_file:    Path to .coverage binary file. Default: ".coverage".
        _cov_factory: Optional callable(data_file) -> Coverage object. For testing.

    Returns:
        HTML string for custom_index.html.

    Raises:
        coverage.exceptions.NoDataError: If data_file does not exist or has no data.
    """
    factory = _cov_factory if _cov_factory is not None else coverage.Coverage
    cov = factory(data_file=data_file)
    cov.load()
    data = cov.get_data()

    # CSS discovery — dynamically find style_cb_*.css (hash changes per coverage version)
    css_files = glob.glob(os.path.join(coverage_dir, "style_cb_*.css"))
    css_href = os.path.basename(css_files[0]) if css_files else ""

    # Build package groups by src/ subpackage (parts[0]="src", parts[1]=pkg)
    packages: dict[str, list[dict]] = defaultdict(list)
    total_stmts = 0
    total_miss = 0

    for abs_path in sorted(data.measured_files()):
        rel = os.path.relpath(abs_path)
        pkg = _package_from_path(rel)

        analysis = cov._analyze(abs_path)
        nums = analysis.numbers
        url = flat_rootname(rel) + ".html"

        packages[pkg].append({
            "rel": rel,
            "url": url,
            "stmts": nums.n_statements,
            "miss": nums.n_missing,
            "branch": nums.n_branches,
            "brpart": nums.n_partial_branches,
            "pct": round(nums.pc_covered),
        })
        total_stmts += nums.n_statements
        total_miss += nums.n_missing

    overall_pct = round((1 - total_miss / total_stmts) * 100) if total_stmts else 0
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return _render_html(packages, css_href, timestamp, overall_pct)


def _package_from_path(rel_path: str) -> str:
    """Extract package name from relative file path.

    Examples:
        "src/actions/action_factory.py" -> "actions"
        "src/ui/pages/dynamic_page.py" -> "ui"
        "top_level.py" -> "root"
    """
    parts = rel_path.replace("\\", "/").split("/")
    return parts[1] if len(parts) > 2 else "root"


def _render_html(
    packages: dict,
    css_href: str,
    timestamp: str,
    overall_pct: int,
) -> str:
    css_link = (
        f'<link rel="stylesheet" href="{escape(css_href)}">'
        if css_href
        else ""
    )
    sections = "".join(
        _render_package(pkg, files)
        for pkg, files in sorted(packages.items())
    )
    return (
        "<!DOCTYPE html><html><head>"
        '<meta charset="utf-8">'
        f"<title>Coverage Drilldown — {timestamp}</title>"
        f"{css_link}"
        "</head><body>"
        f"<h1>Coverage Drilldown — {timestamp}</h1>"
        f"<p>Overall: {overall_pct}%</p>"
        f"{sections}"
        "</body></html>"
    )


def _render_package(pkg: str, files: list) -> str:
    pkg_stmts = sum(f["stmts"] for f in files)
    pkg_miss = sum(f["miss"] for f in files)
    pkg_pct = round((1 - pkg_miss / pkg_stmts) * 100) if pkg_stmts else 0
    rows = "".join(_render_row(f) for f in files)
    return (
        "<details open>"
        f"<summary><b>{escape(pkg)}/ ({pkg_pct}%)</b>"
        f" — {len(files)} files, {pkg_stmts} stmts</summary>"
        "<table><thead><tr>"
        "<th>File</th><th>Stmts</th><th>Miss</th>"
        "<th>Branch</th><th>BrPart</th><th>Cover%</th>"
        "</tr></thead>"
        f"<tbody>{rows}</tbody></table>"
        "</details>"
    )


def _render_row(f: dict) -> str:
    return (
        "<tr>"
        f'<td><a href="{escape(f["url"])}">{escape(f["rel"])}</a></td>'
        f"<td>{f['stmts']}</td>"
        f"<td>{f['miss']}</td>"
        f"<td>{f['branch']}</td>"
        f"<td>{f['brpart']}</td>"
        f"<td>{f['pct']}%</td>"
        "</tr>"
    )
