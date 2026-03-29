#!/usr/bin/env python3
"""
Eval Runner — IDE-agnostic test runner for skills.

Reads test prompts from evals.json, creates a structured workspace
for capturing outputs, and generates a review summary.

Works without claude -p or any IDE-specific tooling.
Designed to be run manually or integrated into any AI IDE workflow.

Usage:
    python eval_runner.py --skill-path ../my-skill/SKILL.md \
                          --evals ../my-skill/evals/evals.json \
                          --output ./my-skill-workspace/iteration-1/

    python eval_runner.py --skill-path ../my-skill/SKILL.md \
                          --evals ../my-skill/evals/evals.json \
                          --output ./my-skill-workspace/iteration-1/ \
                          --grade
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


def load_evals(evals_path: str) -> dict:
    """Load evals.json and return parsed content."""
    with open(evals_path, "r", encoding="utf-8") as f:
        return json.load(f)


def create_workspace(output_dir: str, evals: list) -> dict:
    """Create directory structure for test outputs."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    structure = {}
    for eval_item in evals:
        eval_id = eval_item["id"]
        name = eval_item.get("name", f"eval-{eval_id}")
        safe_name = name.replace(" ", "-").lower()

        eval_dir = output_path / safe_name
        with_skill = eval_dir / "with_skill" / "outputs"
        without_skill = eval_dir / "without_skill" / "outputs"

        with_skill.mkdir(parents=True, exist_ok=True)
        without_skill.mkdir(parents=True, exist_ok=True)

        # Write eval metadata
        metadata = {
            "eval_id": eval_id,
            "eval_name": name,
            "prompt": eval_item["prompt"],
            "expected_output": eval_item.get("expected_output", ""),
            "assertions": eval_item.get("assertions", []),
        }
        with open(eval_dir / "eval_metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        structure[eval_id] = {
            "name": safe_name,
            "dir": str(eval_dir),
            "with_skill": str(with_skill),
            "without_skill": str(without_skill),
        }

    return structure


def generate_test_instructions(skill_path: str, evals: list, structure: dict) -> str:
    """Generate human-readable test instructions."""
    lines = [
        "# Test Instructions",
        "",
        f"Skill: {skill_path}",
        f"Generated: {datetime.now().isoformat()}",
        "",
        "## How to Test",
        "",
        "For each test case below:",
        "1. Open a new AI chat session in your IDE",
        "2. Make sure the skill is accessible",
        "3. Paste the test prompt",
        "4. Save any output files to the `with_skill/outputs/` directory",
        "5. (Optional) Run the same prompt WITHOUT the skill and save to `without_skill/outputs/`",
        "",
        "---",
        "",
    ]

    for eval_item in evals:
        eval_id = eval_item["id"]
        info = structure[eval_id]
        lines.extend([
            f"## Test Case {eval_id}: {info['name']}",
            "",
            f"**Prompt:**",
            f"```",
            eval_item["prompt"],
            f"```",
            "",
            f"**Expected output:** {eval_item.get('expected_output', 'N/A')}",
            "",
            f"**Save with-skill outputs to:** `{info['with_skill']}`",
            f"**Save without-skill outputs to:** `{info['without_skill']}`",
            "",
            "---",
            "",
        ])

    return "\n".join(lines)


def grade_outputs(output_dir: str) -> dict:
    """
    Basic grading: check if output files exist for each eval.
    For assertion-based grading, outputs need manual or AI review.
    """
    output_path = Path(output_dir)
    results = {"graded_at": datetime.now().isoformat(), "evals": []}

    for eval_dir in sorted(output_path.iterdir()):
        if not eval_dir.is_dir():
            continue

        metadata_path = eval_dir / "eval_metadata.json"
        if not metadata_path.exists():
            continue

        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        with_skill_outputs = list((eval_dir / "with_skill" / "outputs").iterdir()) if (eval_dir / "with_skill" / "outputs").exists() else []
        without_skill_outputs = list((eval_dir / "without_skill" / "outputs").iterdir()) if (eval_dir / "without_skill" / "outputs").exists() else []

        eval_result = {
            "eval_id": metadata["eval_id"],
            "eval_name": metadata["eval_name"],
            "with_skill_files": [f.name for f in with_skill_outputs],
            "without_skill_files": [f.name for f in without_skill_outputs],
            "has_with_skill_output": len(with_skill_outputs) > 0,
            "has_without_skill_output": len(without_skill_outputs) > 0,
            "assertions": [],
        }

        # Check file_exists assertions
        for assertion in metadata.get("assertions", []):
            if assertion.get("type") == "file_exists":
                target = assertion.get("target", "")
                exists = any(f.name == target for f in with_skill_outputs)
                eval_result["assertions"].append({
                    "text": assertion.get("name", assertion.get("check", "file_exists")),
                    "passed": exists,
                    "evidence": f"File '{target}' {'found' if exists else 'not found'} in outputs",
                })
            elif assertion.get("type") == "content_contains":
                target = assertion.get("target", "")
                check = assertion.get("check", "")
                found = False
                for f in with_skill_outputs:
                    try:
                        content = f.read_text(encoding="utf-8")
                        if target in content:
                            found = True
                            break
                    except (UnicodeDecodeError, IsADirectoryError):
                        continue
                eval_result["assertions"].append({
                    "text": assertion.get("name", assertion.get("check", "content_contains")),
                    "passed": found,
                    "evidence": f"Content '{target}' {'found' if found else 'not found'} in output files",
                })
            else:
                eval_result["assertions"].append({
                    "text": assertion.get("name", assertion.get("check", "unknown")),
                    "passed": None,
                    "evidence": "Requires manual review",
                })

        results["evals"].append(eval_result)

    return results


def generate_summary(output_dir: str, results: dict) -> str:
    """Generate a markdown summary of test results."""
    lines = [
        "# Eval Results Summary",
        "",
        f"Generated: {results['graded_at']}",
        "",
        "| Eval | With Skill | Without Skill | Assertions |",
        "|------|-----------|---------------|------------|",
    ]

    for ev in results["evals"]:
        with_status = f"{len(ev['with_skill_files'])} files" if ev["has_with_skill_output"] else "No output"
        without_status = f"{len(ev['without_skill_files'])} files" if ev["has_without_skill_output"] else "No output"

        assertion_parts = []
        for a in ev["assertions"]:
            if a["passed"] is True:
                assertion_parts.append(f"PASS: {a['text']}")
            elif a["passed"] is False:
                assertion_parts.append(f"FAIL: {a['text']}")
            else:
                assertion_parts.append(f"MANUAL: {a['text']}")
        assertion_str = "; ".join(assertion_parts) if assertion_parts else "None"

        lines.append(f"| {ev['eval_name']} | {with_status} | {without_status} | {assertion_str} |")

    lines.extend(["", "## Next Steps", "", "1. Review the outputs in each eval directory",
                   "2. Add feedback to `feedback.json` in the workspace root",
                   "3. Re-run after improving the skill"])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Eval Runner for AI Skills")
    parser.add_argument("--skill-path", required=True, help="Path to the SKILL.md file")
    parser.add_argument("--evals", required=True, help="Path to evals.json")
    parser.add_argument("--output", required=True, help="Output directory for this iteration")
    parser.add_argument("--grade", action="store_true", help="Grade existing outputs (run after testing)")
    args = parser.parse_args()

    evals_data = load_evals(args.evals)
    evals_list = evals_data.get("evals", [])

    if not evals_list:
        print("No evals found in", args.evals)
        sys.exit(1)

    if args.grade:
        # Grade mode: check outputs that already exist
        print(f"Grading outputs in {args.output}...")
        results = grade_outputs(args.output)

        grading_path = Path(args.output) / "grading_summary.json"
        with open(grading_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        summary = generate_summary(args.output, results)
        summary_path = Path(args.output) / "summary.md"
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary)

        print(f"Grading complete. See:")
        print(f"  {grading_path}")
        print(f"  {summary_path}")
    else:
        # Setup mode: create workspace and instructions
        print(f"Creating workspace in {args.output}...")
        structure = create_workspace(args.output, evals_list)

        instructions = generate_test_instructions(args.skill_path, evals_list, structure)
        instructions_path = Path(args.output) / "TEST_INSTRUCTIONS.md"
        with open(instructions_path, "w", encoding="utf-8") as f:
            f.write(instructions)

        print(f"Workspace ready. {len(evals_list)} test cases created.")
        print(f"Read {instructions_path} for testing instructions.")
        print(f"\nAfter testing, run with --grade to check results:")
        print(f"  python {sys.argv[0]} --skill-path {args.skill_path} --evals {args.evals} --output {args.output} --grade")


if __name__ == "__main__":
    main()
