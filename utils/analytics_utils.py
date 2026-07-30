"""
Aggregation helpers that turn raw attendance/student rows into the numbers
shown on the Dashboard and Analytics pages.
"""
from collections import defaultdict


def compute_dashboard_summary(students, today_records):
    total_students = len(students)
    present_today = sum(1 for r in today_records if r["status"] == "Present")
    absent_today = total_students - present_today if total_students else 0
    percentage = round((present_today / total_students) * 100, 2) if total_students else 0.0

    return {
        "total_students": total_students,
        "present_today": present_today,
        "absent_today": max(absent_today, 0),
        "attendance_percentage": percentage,
    }


def compute_student_wise_percentage(students, all_records):
    """Returns list of {student_id, name, present, total, percentage} sorted desc."""
    counts = defaultdict(lambda: {"present": 0, "total": 0})
    for r in all_records:
        key = r["student_id"]
        counts[key]["total"] += 1
        if r["status"] == "Present":
            counts[key]["present"] += 1

    student_map = {s["id"]: s["name"] for s in students}
    result = []
    for sid, name in student_map.items():
        c = counts.get(sid, {"present": 0, "total": 0})
        pct = round((c["present"] / c["total"]) * 100, 2) if c["total"] else 0.0
        result.append({
            "student_id": sid,
            "name": name,
            "present": c["present"],
            "total": c["total"],
            "percentage": pct,
        })
    result.sort(key=lambda x: x["percentage"], reverse=True)
    return result


def compute_daily_trend(all_records):
    """Returns {date_str: {'present': n, 'absent': n}} ordered by date."""
    trend = defaultdict(lambda: {"present": 0, "absent": 0})
    for r in all_records:
        date_str = str(r["attendance_date"])
        if r["status"] == "Present":
            trend[date_str]["present"] += 1
        else:
            trend[date_str]["absent"] += 1
    return dict(sorted(trend.items()))


def compute_monthly_trend(all_records):
    """Returns {'YYYY-MM': {'present': n, 'absent': n}} ordered by month."""
    trend = defaultdict(lambda: {"present": 0, "absent": 0})
    for r in all_records:
        month_key = str(r["attendance_date"])[:7]
        if r["status"] == "Present":
            trend[month_key]["present"] += 1
        else:
            trend[month_key]["absent"] += 1
    return dict(sorted(trend.items()))


def highest_lowest_attendance(student_wise_percentages):
    if not student_wise_percentages:
        return None, None
    with_records = [s for s in student_wise_percentages if s["total"] > 0]
    if not with_records:
        return None, None
    highest = max(with_records, key=lambda x: x["percentage"])
    lowest = min(with_records, key=lambda x: x["percentage"])
    return highest, lowest
