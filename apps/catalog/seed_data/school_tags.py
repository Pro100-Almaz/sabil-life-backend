"""School tag taxonomy — the filter vocabulary for SCHOOLS listings.

Grouped by facet for readability and so a future ListingTag.facet column
can be populated without re-deriving anything. ``ListingTag`` itself only
stores ``name`` + ``category``, so :data:`SCHOOL_TAGS` is what gets written.

Every tag here is used by at least one school in ``schools.SCHOOLS`` — the
generator drops unused ones so the app never renders a dead filter chip.
"""

SCHOOL_TAG_FACETS: dict[str, tuple[str, ...]] = {
    "Curriculum": (
        "American Curriculum",
        "British Curriculum",
        "CBSE",
        "Cambridge",
        "Canadian Curriculum",
        "French Curriculum",
        "German Curriculum",
        "IB",
        "International Curriculum",
        "Japanese Curriculum",
        "Lebanese Curriculum",
        "Montessori",
        "Pakistani Curriculum",
        "Philippine Curriculum",
        "SABIS",
        "Sri Lankan Curriculum",
        "Turkish Curriculum",
    ),
    "Qualification": (
        "A Levels",
        "AP",
        "Baccalaureat",
        "IB Diploma",
        "IGCSE",
    ),
    "Stage": (
        "Early Years",
        "Full Pathway",
        "Primary Only",
        "Secondary",
    ),
    "Gender": (
        "Boys Only",
        "Co-ed",
        "Girls Only",
    ),
    "Network": (
        "AEFE",
        "British Schools Overseas",
        "CBSE Affiliated",
        "Cambridge International",
        "GEMS Education",
        "IB World School",
        "Nord Anglia",
        "Podar Network",
        "Qatar Foundation",
        "SABIS Network",
    ),
    "Character": (
        "Bilingual Arabic-English",
        "Community School",
        "Islamic Studies",
        "Multilingual",
    ),
    "Facilities": (
        "Arts",
        "ICT & Technology",
        "Innovation Labs",
        "Library",
        "Outdoor Learning",
        "Performing Arts",
        "STEM & STEAM",
        "Science Labs",
        "Sports Facilities",
        "Swimming Pool",
    ),
    "Fees": (
        "Budget (under 15k)",
        "Elite (45k+)",
        "Mid-Range (15-30k)",
        "Premium (30-45k)",
    ),
}

# Flat, de-duplicated tuple in facet order — the import_tags write set.
SCHOOL_TAGS: tuple[str, ...] = tuple(
    dict.fromkeys(name for names in SCHOOL_TAG_FACETS.values() for name in names)
)
