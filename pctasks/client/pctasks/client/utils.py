def status_emoji(status: str) -> str:
    if status.lower() == "completed":
        return "✅"
    if status.lower() == "failed":
        return "❌"
    if status.lower() == "running":
        return "🏃"
    if status.lower() == "cancelled":
        return "🚫"
    if status.lower() == "skipped":
        return "⏭️"
    else:
        return "🕖"
