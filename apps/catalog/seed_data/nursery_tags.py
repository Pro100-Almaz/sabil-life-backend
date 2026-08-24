"""Nursery tag taxonomy and conservative tag inference for seed listings."""

from collections.abc import Mapping

NURSERY_TAG_FACETS: dict[str, tuple[str, ...]] = {
    "Curriculum": (
        "Montessori",
        "EYFS",
        "British Curriculum",
        "International Curriculum",
        "Reggio Emilia",
        "Arabic Curriculum",
    ),
    "Age Group": (
        "Infant Care",
        "Toddler Care",
        "Preschool",
        "Daycare",
    ),
    "Language": (
        "English-speaking",
        "Arabic-speaking",
        "French-speaking",
        "Bilingual",
    ),
    "Schedule": (
        "Full-day",
        "Half-day",
        "Flexible Hours",
        "Weekend Care",
    ),
    "Services": (
        "Meals Included",
        "Transportation",
        "After-school Care",
        "Potty Training Support",
    ),
    "Facilities": (
        "Outdoor Play",
        "Indoor Play Area",
        "CCTV",
        "Parent App",
    ),
    "Support & Safety": (
        "Special Needs Support",
        "First Aid Trained",
        "Female Staff",
        "Licensed",
        "Accepting Enrollments",
    ),
}

NURSERY_TAGS: tuple[str, ...] = tuple(
    dict.fromkeys(name for names in NURSERY_TAG_FACETS.values() for name in names)
)


def nursery_seed_tags(record: Mapping) -> tuple[str, ...]:
    """Return only tags supported by a nursery seed record's explicit data."""
    tags = list(record.get("tags", ()))
    age_groups = record.get("age_groups", ())
    title = str(record.get("title", "")).lower()

    if "0-3" in age_groups:
        tags.extend(("Infant Care", "Toddler Care"))
    if "3-5" in age_groups:
        tags.append("Preschool")
    if "montessori" in title:
        tags.append("Montessori")
    if "british" in title:
        tags.extend(("British Curriculum", "English-speaking"))
    elif "english" in title:
        tags.append("English-speaking")
    if "french" in title:
        tags.append("French-speaking")
    if "international" in title:
        tags.append("International Curriculum")

    return tuple(dict.fromkeys(tags))
