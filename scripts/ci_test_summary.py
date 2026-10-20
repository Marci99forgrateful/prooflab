"""Expose actual JUnit outcomes through GitHub annotations, preserving failures."""

from __future__ import annotations

import sys
from pathlib import Path
from xml.etree import ElementTree


def escape(message: str) -> str:
    return message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def main() -> int:
    path = Path(sys.argv[1])
    if not path.exists():
        print("::warning::JUnit report unavailable; inspect the preceding failed setup/test step")
        return 0
    root = ElementTree.parse(path).getroot()
    suites = list(root.findall("testsuite")) if root.tag == "testsuites" else [root]
    counts = {
        name: sum(int(s.get(name, "0")) for s in suites)
        for name in ("tests", "failures", "errors", "skipped")
    }
    print("::notice title=Actual Pytest outcomes::" + escape(str(counts)))
    for test in root.iter("testcase"):
        for kind in ("failure", "error"):
            detail = test.find(kind)
            if detail is not None:
                label = f"{test.get('classname')}.{test.get('name')}"
                print(
                    "::error title=Pytest "
                    + kind
                    + "::"
                    + escape(label + "\n" + (detail.text or detail.get("message", ""))[:6000])
                )
    if counts["tests"] <= counts["skipped"]:
        print("::error::No tests executed; a zero-test or all-skipped run is not validation")
        return 1
    return int(bool(counts["failures"] or counts["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
