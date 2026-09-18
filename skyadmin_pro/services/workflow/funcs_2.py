from __future__ import annotations

from datetime import date


def format_eod_report(
    tasks: list[dict],
    pipeline: list[dict] | None = None,
    when: date | None = None,
) -> str:
    stamp = when or date.today()
    header = f"SkyAdmin Pro — EOD Report\n{stamp.strftime('%d %B %Y')}"
    if not tasks and not pipeline:
        return f"{header}\n\nNo tasks or pipeline steps completed today."

    sections = [header, ""]
    if tasks:
        ordered = sorted(tasks, key=lambda item: item.get("completed_at") or "")
        sections.append(f"Completed today ({len(ordered)}):")
        sections.append("")
        for index, task in enumerate(ordered, start=1):
            client = (task.get("client_name") or "").strip() or "Unassigned"
            title = (task.get("title") or "Task").strip()
            sections.append(f"{index}. {client}: {title} - Completed")
    if pipeline:
        sections.append("")
        sections.append(f"Pipeline completed today ({len(pipeline)}):")
        sections.append("")
        for index, item in enumerate(pipeline, start=1):
            client = (item.get("client_name") or "").strip() or "Unassigned"
            service = (item.get("service") or "Service").strip()
            sections.append(f"{index}. {client}: {service} - Pipeline complete")
    return "\n".join(sections)
