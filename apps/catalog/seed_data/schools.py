"""The 84 Qatar schools from ``SabilLife_Schools.md``, normalised for seeding.

Derived once from the markdown source and committed as data — the markdown
lives outside this repo, so parsing it at runtime would make the importer
depend on a file that is absent in CI and production.

``lat`` / ``lng`` are DISTRICT CENTROIDS, not geocoded school addresses.
The source has no coordinates, so each school inherits the centre point of
its district, accurate to roughly 1-2 km. That is enough for "which schools
are in my part of town" (``?sort=distance``, ``max_distance_km``) and wrong
for anything finer: all five Al Waab schools share one point, so their order
within the district is arbitrary. Replace with a real geocoding pass before
the app promises precise distances.

29 schools have ``lat``/``lng`` of None. 28 of them list only "Doha" as their
location and the metro is ~25 km across, so a single city point would report
a school 15 km away as 2 km away; the 29th lists "Doha / Lusail" and picking
one would be a guess. NULL coordinates drop a listing out of distance-sorted
results rather than misplacing it. Narrowing those locations in the source
markdown is what fixes them.

Also absent from the source and NOT invented here:
  * ``rating`` / ``review_count`` — left at model defaults (0.0 / 0).

``price_from_qar`` is the annual fee floor: the source gives open-ended
bands ("18,000+"), so the number is a lower bound, not an exact fee.
"""

from apps.catalog.models import ListingCategory

CATEGORY = ListingCategory.SCHOOLS

SCHOOLS: tuple[dict, ...] = (
    {
        "slug": "schools-acs-international-school-doha",
        "title": "ACS International School Doha",
        "subtitle": "IB / American pathways, Doha",
        "neighborhood": "Doha",
        "lat": None,
        "lng": None,
        "price_from_qar": 50000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Premium international school with strong university preparation. Offers IB / American pathways from Pre-K–Grade 12, for ages 3–18. Recognition: International school network."
        ),
        "highlights": ["STEM labs", "Sports", "Arts", "Library"],
        "tags": ["American Curriculum", "Arts", "Co-ed", "Early Years", "Elite (45k+)", "Full Pathway", "IB", "IB Diploma", "Library", "STEM & STEAM", "Science Labs", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-al-arqam-academy",
        "title": "Al Arqam Academy",
        "subtitle": "British-based with Islamic studies, Abu Hamour",
        "neighborhood": "Abu Hamour",
        "lat": 25.2286,
        "lng": 51.4869,
        "price_from_qar": 15000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Combines English education with Islamic values. Offers British-based with Islamic studies from KG–Grade 12, for ages 3–18. Recognition: Qatar private school system."
        ),
        "highlights": ["Classrooms", "Sports facilities", "Islamic learning areas"],
        "tags": ["A Levels", "British Curriculum", "Co-ed", "Early Years", "Full Pathway", "IGCSE", "Islamic Studies", "Mid-Range (15-30k)", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-al-hekma-international-school",
        "title": "Al Hekma International School",
        "subtitle": "American Curriculum, Al Mamoura",
        "neighborhood": "Al Mamoura",
        "lat": 25.2419,
        "lng": 51.5008,
        "price_from_qar": 20000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "American-style education with Arabic and Islamic studies. Offers American Curriculum from Pre-K–Grade 12, for ages 3–18. Recognition: American curriculum school."
        ),
        "highlights": ["Science labs", "ICT", "Activities"],
        "tags": ["American Curriculum", "Bilingual Arabic-English", "Co-ed", "Early Years", "Full Pathway", "ICT & Technology", "Islamic Studies", "Mid-Range (15-30k)", "Science Labs", "Secondary"],
    },
    {
        "slug": "schools-al-khor-international-school",
        "title": "Al Khor International School",
        "subtitle": "British / IB pathways, Al Khor",
        "neighborhood": "Al Khor",
        "lat": 25.684,
        "lng": 51.497,
        "price_from_qar": 25000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "One of Qatar’s largest international schools. Offers British / IB pathways from Foundation–Year 13, for ages 3–18. Recognition: International school."
        ),
        "highlights": ["Large campus", "Sports facilities", "Performing arts"],
        "tags": ["A Levels", "Arts", "British Curriculum", "Co-ed", "Early Years", "Full Pathway", "IB", "IB Diploma", "IGCSE", "Mid-Range (15-30k)", "Performing Arts", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-al-maha-academy-for-boys",
        "title": "Al Maha Academy for Boys",
        "subtitle": "British Curriculum, Al Waab",
        "neighborhood": "Al Waab",
        "lat": 25.2606,
        "lng": 51.4494,
        "price_from_qar": 22000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Boys’ British school. Offers British Curriculum from Foundation–Year 13, for ages 3–18. Recognition: British curriculum."
        ),
        "highlights": ["Sports", "Science labs", "ICT"],
        "tags": ["A Levels", "Boys Only", "British Curriculum", "Early Years", "Full Pathway", "ICT & Technology", "IGCSE", "Mid-Range (15-30k)", "Science Labs", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-al-maha-academy-for-girls",
        "title": "Al Maha Academy for Girls",
        "subtitle": "British Curriculum, Al Waab",
        "neighborhood": "Al Waab",
        "lat": 25.2606,
        "lng": 51.4494,
        "price_from_qar": 22000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Girls’ British school. Offers British Curriculum from Foundation–Year 13, for ages 3–18. Recognition: British curriculum."
        ),
        "highlights": ["Arts", "Sports", "STEM facilities"],
        "tags": ["A Levels", "Arts", "British Curriculum", "Early Years", "Full Pathway", "Girls Only", "IGCSE", "Mid-Range (15-30k)", "STEM & STEAM", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-al-nebras-international-school",
        "title": "Al Nebras International School",
        "subtitle": "Montessori / International, Doha / Lusail",
        "neighborhood": "Doha / Lusail",
        "lat": None,
        "lng": None,
        "price_from_qar": 30000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Child-centred learning approach. Offers Montessori / International from Early Years–Secondary, for ages 3–18. Recognition: Montessori-based education."
        ),
        "highlights": ["Montessori classrooms", "Activity spaces"],
        "tags": ["Co-ed", "Early Years", "Full Pathway", "Montessori", "Premium (30-45k)", "Secondary"],
    },
    {
        "slug": "schools-al-rowad-international-school",
        "title": "Al Rowad International School",
        "subtitle": "American Curriculum, Abu Hamour",
        "neighborhood": "Abu Hamour",
        "lat": 25.2286,
        "lng": 51.4869,
        "price_from_qar": 18000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "American-style education. Offers American Curriculum from KG–Grade 12, for ages 3–18. Recognition: American curriculum."
        ),
        "highlights": ["ICT", "Sports", "Clubs"],
        "tags": ["American Curriculum", "Co-ed", "Early Years", "Full Pathway", "ICT & Technology", "Mid-Range (15-30k)", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-al-wataniya-international-school",
        "title": "Al Wataniya International School",
        "subtitle": "British Primary Curriculum, Doha",
        "neighborhood": "Doha",
        "lat": None,
        "lng": None,
        "price_from_qar": 27000,
        "age_groups": ["3-5", "6-12"],
        "description": (
            "Specialist British primary school. Offers British Primary Curriculum from FS1–Year 6, for ages 3–11. Recognition: British curriculum."
        ),
        "highlights": ["Primary learning spaces", "Library", "Sports"],
        "tags": ["British Curriculum", "Co-ed", "Early Years", "Library", "Mid-Range (15-30k)", "Primary Only", "Sports Facilities"],
    },
    {
        "slug": "schools-american-academy-school-qatar",
        "title": "American Academy School Qatar",
        "subtitle": "American Curriculum, Doha",
        "neighborhood": "Doha",
        "lat": None,
        "lng": None,
        "price_from_qar": 18000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "American pathway school. Offers American Curriculum from KG–Grade 12, for ages 3–18. Recognition: American curriculum."
        ),
        "highlights": ["Technology", "Sports", "Activities"],
        "tags": ["American Curriculum", "Co-ed", "Early Years", "Full Pathway", "ICT & Technology", "Mid-Range (15-30k)", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-american-school-of-doha",
        "title": "American School of Doha",
        "subtitle": "American Curriculum (AP), Al Waab",
        "neighborhood": "Al Waab",
        "lat": 25.2606,
        "lng": 51.4494,
        "price_from_qar": 45000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "One of Qatar’s leading American schools. Offers American Curriculum (AP) from Pre-K–Grade 12, for ages 3–18. Recognition: Internationally recognised American school."
        ),
        "highlights": ["Innovation labs", "Athletics", "Arts"],
        "tags": ["AP", "American Curriculum", "Arts", "Co-ed", "Early Years", "Elite (45k+)", "Full Pathway", "Innovation Labs", "Science Labs", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-arab-international-academy",
        "title": "Arab International Academy",
        "subtitle": "IB Curriculum, Al Luqta",
        "neighborhood": "Al Luqta",
        "lat": 25.3236,
        "lng": 51.4602,
        "price_from_qar": 45000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "IB education with Arabic cultural focus. Offers IB Curriculum from Early Years–Grade 12, for ages 3–18. Recognition: IB World School."
        ),
        "highlights": ["Modern campus", "Bilingual facilities"],
        "tags": ["Bilingual Arabic-English", "Co-ed", "Early Years", "Elite (45k+)", "Full Pathway", "IB", "IB Diploma", "IB World School", "Secondary"],
    },
    {
        "slug": "schools-awfaz-global-school",
        "title": "Awfaz Global School",
        "subtitle": "International Curriculum, Doha",
        "neighborhood": "Doha",
        "lat": None,
        "lng": None,
        "price_from_qar": 18000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "International learning environment. Offers International Curriculum from KG–Grade 12, for ages 3–18. Recognition: Qatar private education system."
        ),
        "highlights": ["Technology", "Activities"],
        "tags": ["Co-ed", "Early Years", "Full Pathway", "ICT & Technology", "International Curriculum", "Mid-Range (15-30k)", "Secondary"],
    },
    {
        "slug": "schools-beta-cambridge-school",
        "title": "Beta Cambridge School",
        "subtitle": "Cambridge / British, Doha",
        "neighborhood": "Doha",
        "lat": None,
        "lng": None,
        "price_from_qar": 18000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Cambridge examination pathway. Offers Cambridge / British from KG–Year 13, for ages 3–18. Recognition: Cambridge pathway."
        ),
        "highlights": ["ICT", "Science facilities"],
        "tags": ["A Levels", "British Curriculum", "Cambridge", "Cambridge International", "Co-ed", "Early Years", "Full Pathway", "ICT & Technology", "IGCSE", "Mid-Range (15-30k)", "Science Labs", "Secondary"],
    },
    {
        "slug": "schools-belgravia-high-school",
        "title": "Belgravia High School",
        "subtitle": "British Curriculum, Doha",
        "neighborhood": "Doha",
        "lat": None,
        "lng": None,
        "price_from_qar": 20000,
        "age_groups": ["6-12", "13-18"],
        "description": (
            "British-style education. Offers British Curriculum from Primary–Secondary, for ages 5–18. Recognition: British curriculum."
        ),
        "highlights": ["Classrooms", "Activities"],
        "tags": ["A Levels", "British Curriculum", "Co-ed", "IGCSE", "Mid-Range (15-30k)", "Secondary"],
    },
    {
        "slug": "schools-birla-public-school",
        "title": "Birla Public School",
        "subtitle": "CBSE, Abu Hamour",
        "neighborhood": "Abu Hamour",
        "lat": 25.2286,
        "lng": 51.4869,
        "price_from_qar": 14000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Established Indian international school. Offers CBSE from KG–Grade 12, for ages 3–18. Recognition: CBSE affiliated."
        ),
        "highlights": ["Laboratories", "Sports", "Auditorium"],
        "tags": ["Budget (under 15k)", "CBSE", "CBSE Affiliated", "Co-ed", "Early Years", "Full Pathway", "Science Labs", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-brilliant-indian-international-school",
        "title": "Brilliant Indian International School",
        "subtitle": "CBSE, Doha",
        "neighborhood": "Doha",
        "lat": None,
        "lng": None,
        "price_from_qar": 12000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Indian curriculum pathway. Offers CBSE from KG–Grade 12, for ages 3–18. Recognition: CBSE affiliated."
        ),
        "highlights": ["Science labs", "Activities"],
        "tags": ["Budget (under 15k)", "CBSE", "CBSE Affiliated", "Co-ed", "Early Years", "Full Pathway", "Science Labs", "Secondary"],
    },
    {
        "slug": "schools-cambridge-international-school-doha",
        "title": "Cambridge International School Doha",
        "subtitle": "Cambridge / British, Doha",
        "neighborhood": "Doha",
        "lat": None,
        "lng": None,
        "price_from_qar": 18000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Cambridge qualifications. Offers Cambridge / British from KG–Year 13, for ages 3–18. Recognition: Cambridge International."
        ),
        "highlights": ["ICT", "Labs", "Sports"],
        "tags": ["A Levels", "British Curriculum", "Cambridge", "Cambridge International", "Co-ed", "Early Years", "Full Pathway", "ICT & Technology", "IGCSE", "Mid-Range (15-30k)", "Science Labs", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-compass-international-school-doha-themaid-campus",
        "title": "Compass International School Doha – Themaid Campus",
        "subtitle": "British / IB pathway, Doha",
        "neighborhood": "Doha",
        "lat": None,
        "lng": None,
        "price_from_qar": 45000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Premium international school. Offers British / IB pathway from Early Years–Year 13, for ages 3–18. Recognition: Nord Anglia Education."
        ),
        "highlights": ["STEAM", "Sports", "Arts"],
        "tags": ["A Levels", "Arts", "British Curriculum", "Co-ed", "Early Years", "Elite (45k+)", "Full Pathway", "IB", "IB Diploma", "IGCSE", "Nord Anglia", "STEM & STEAM", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-compass-international-school-doha-madinat-khalifa-campus",
        "title": "Compass International School Doha – Madinat Khalifa Campus",
        "subtitle": "British Curriculum, Doha",
        "neighborhood": "Doha",
        "lat": None,
        "lng": None,
        "price_from_qar": 40000,
        "age_groups": ["3-5", "6-12"],
        "description": (
            "Primary specialist campus. Offers British Curriculum from Early Years–Year 6, for ages 3–11. Recognition: Nord Anglia Education."
        ),
        "highlights": ["Primary facilities"],
        "tags": ["British Curriculum", "Co-ed", "Early Years", "Nord Anglia", "Premium (30-45k)", "Primary Only"],
    },
    {
        "slug": "schools-compass-international-school-doha-gharaffa-campus",
        "title": "Compass International School Doha – Gharaffa Campus",
        "subtitle": "British Curriculum, Al Gharrafa",
        "neighborhood": "Al Gharrafa",
        "lat": 25.3339,
        "lng": 51.4408,
        "price_from_qar": 40000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Full pathway campus. Offers British Curriculum from Early Years–Year 13, for ages 3–18. Recognition: Nord Anglia Education."
        ),
        "highlights": ["Sports", "Science", "Arts"],
        "tags": ["A Levels", "Arts", "British Curriculum", "Co-ed", "Early Years", "Full Pathway", "IGCSE", "Nord Anglia", "Premium (30-45k)", "Science Labs", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-doha-academy",
        "title": "Doha Academy",
        "subtitle": "British Curriculum (Cambridge/Pearson), Al Waab",
        "neighborhood": "Al Waab",
        "lat": 25.2606,
        "lng": 51.4494,
        "price_from_qar": 24000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Established British school offering IGCSE and A Levels. Offers British Curriculum (Cambridge/Pearson) from EYFS–Year 13, for ages 3–18. Recognition: British curriculum school."
        ),
        "highlights": ["Science labs", "Sports", "Arts"],
        "tags": ["A Levels", "Arts", "British Curriculum", "Cambridge", "Co-ed", "Early Years", "Full Pathway", "IGCSE", "Mid-Range (15-30k)", "Science Labs", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-doha-british-school-ain-khaled",
        "title": "Doha British School – Ain Khaled",
        "subtitle": "British National Curriculum, Ain Khaled",
        "neighborhood": "Ain Khaled",
        "lat": 25.2244,
        "lng": 51.4525,
        "price_from_qar": 33000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "One of Qatar’s leading British schools. Offers British National Curriculum from FS1–Year 13, for ages 3–18. Recognition: British Schools Overseas recognised."
        ),
        "highlights": ["Sports facilities", "Performing arts", "Labs"],
        "tags": ["A Levels", "Arts", "British Curriculum", "British Schools Overseas", "Co-ed", "Early Years", "Full Pathway", "IGCSE", "Performing Arts", "Premium (30-45k)", "Science Labs", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-doha-british-school-al-wakra",
        "title": "Doha British School – Al Wakra",
        "subtitle": "British National Curriculum, Al Wakrah",
        "neighborhood": "Al Wakrah",
        "lat": 25.1659,
        "lng": 51.5988,
        "price_from_qar": 31000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Serves families in southern Qatar. Offers British National Curriculum from FS1–Year 13, for ages 3–18. Recognition: British curriculum."
        ),
        "highlights": ["Sports", "ICT", "Arts"],
        "tags": ["A Levels", "Arts", "British Curriculum", "Co-ed", "Early Years", "Full Pathway", "ICT & Technology", "IGCSE", "Premium (30-45k)", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-doha-british-school-rawdat-al-hamama",
        "title": "Doha British School – Rawdat Al Hamama",
        "subtitle": "British National Curriculum, Rawdat Al Hamama",
        "neighborhood": "Rawdat Al Hamama",
        "lat": 25.4247,
        "lng": 51.4694,
        "price_from_qar": 34000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Newer DBS campus. Offers British National Curriculum from FS1–Year 13, for ages 3–18. Recognition: British curriculum."
        ),
        "highlights": ["Modern campus", "Sports", "Technology"],
        "tags": ["A Levels", "British Curriculum", "Co-ed", "Early Years", "Full Pathway", "ICT & Technology", "IGCSE", "Premium (30-45k)", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-doha-college",
        "title": "Doha College",
        "subtitle": "British Curriculum (IGCSE/A Levels), West Bay Lagoon",
        "neighborhood": "West Bay Lagoon",
        "lat": 25.3739,
        "lng": 51.5133,
        "price_from_qar": 42000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "One of Qatar’s highest-performing British schools. Offers British Curriculum (IGCSE/A Levels) from FS1–Year 13, for ages 3–18. Recognition: British Schools Overseas recognised."
        ),
        "highlights": ["Olympic-size pool", "Sports", "Arts", "Innovation spaces"],
        "tags": ["A Levels", "Arts", "British Curriculum", "British Schools Overseas", "Co-ed", "Early Years", "Full Pathway", "IGCSE", "Innovation Labs", "Premium (30-45k)", "Secondary", "Sports Facilities", "Swimming Pool"],
    },
    {
        "slug": "schools-doha-english-speaking-school-dess",
        "title": "Doha English Speaking School (DESS)",
        "subtitle": "British Primary Curriculum, Fereej Kulaib",
        "neighborhood": "Fereej Kulaib",
        "lat": 25.2842,
        "lng": 51.5289,
        "price_from_qar": 35000,
        "age_groups": ["3-5", "6-12"],
        "description": (
            "Prestigious British preparatory school. Offers British Primary Curriculum from FS1–Year 8, for ages 3–13. Recognition: British Schools Overseas recognised."
        ),
        "highlights": ["Library", "Sports", "Arts"],
        "tags": ["Arts", "British Curriculum", "British Schools Overseas", "Co-ed", "Early Years", "Library", "Premium (30-45k)", "Primary Only", "Sports Facilities"],
    },
    {
        "slug": "schools-dukhan-english-school",
        "title": "Dukhan English School",
        "subtitle": "British Curriculum, Dukhan",
        "neighborhood": "Dukhan",
        "lat": 25.43,
        "lng": 50.785,
        "price_from_qar": 25000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Community school serving western Qatar. Offers British Curriculum from Nursery–Year 13, for ages 3–18. Recognition: British curriculum."
        ),
        "highlights": ["Sports", "Labs", "Performing arts"],
        "tags": ["A Levels", "Arts", "British Curriculum", "Co-ed", "Community School", "Early Years", "Full Pathway", "IGCSE", "Mid-Range (15-30k)", "Performing Arts", "Science Labs", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-durham-school-for-girls-doha",
        "title": "Durham School for Girls Doha",
        "subtitle": "British Curriculum, Mesaimeer",
        "neighborhood": "Mesaimeer",
        "lat": 25.2231,
        "lng": 51.4886,
        "price_from_qar": 27000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Girls-only British school. Offers British Curriculum from FS1–Year 13, for ages 3–18. Recognition: British curriculum."
        ),
        "highlights": ["STEM", "Sports", "Arts"],
        "tags": ["A Levels", "Arts", "British Curriculum", "Early Years", "Full Pathway", "Girls Only", "IGCSE", "Mid-Range (15-30k)", "STEM & STEAM", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-edison-international-academy",
        "title": "Edison International Academy",
        "subtitle": "British Curriculum, Doha",
        "neighborhood": "Doha",
        "lat": None,
        "lng": None,
        "price_from_qar": 20000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "British pathway school. Offers British Curriculum from EYFS–Year 13, for ages 3–18. Recognition: British curriculum."
        ),
        "highlights": ["ICT", "Science labs", "Activities"],
        "tags": ["A Levels", "British Curriculum", "Co-ed", "Early Years", "Full Pathway", "ICT & Technology", "IGCSE", "Mid-Range (15-30k)", "Science Labs", "Secondary"],
    },
    {
        "slug": "schools-english-modern-school-abu-hamour",
        "title": "English Modern School – Abu Hamour",
        "subtitle": "British & CBSE pathways, Abu Hamour",
        "neighborhood": "Abu Hamour",
        "lat": 25.2286,
        "lng": 51.4869,
        "price_from_qar": 16000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Offers multiple curriculum pathways. Offers British & CBSE pathways from KG–Grade 12, for ages 3–18. Recognition: Qatar private education system."
        ),
        "highlights": ["Labs", "Sports", "Technology"],
        "tags": ["A Levels", "British Curriculum", "CBSE", "Co-ed", "Early Years", "Full Pathway", "ICT & Technology", "IGCSE", "Mid-Range (15-30k)", "Science Labs", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-english-modern-school-al-khor",
        "title": "English Modern School – Al Khor",
        "subtitle": "British & CBSE pathways, Al Khor",
        "neighborhood": "Al Khor",
        "lat": 25.684,
        "lng": 51.497,
        "price_from_qar": 15000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Northern Qatar campus. Offers British & CBSE pathways from KG–Grade 12, for ages 3–18. Recognition: Qatar private education system."
        ),
        "highlights": ["Sports", "Labs", "Activities"],
        "tags": ["A Levels", "British Curriculum", "CBSE", "Co-ed", "Early Years", "Full Pathway", "IGCSE", "Mid-Range (15-30k)", "Science Labs", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-gems-american-academy-qatar",
        "title": "GEMS American Academy Qatar",
        "subtitle": "American Curriculum (AP), Al Luqta",
        "neighborhood": "Al Luqta",
        "lat": 25.3236,
        "lng": 51.4602,
        "price_from_qar": 42000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Premium American school. Offers American Curriculum (AP) from Pre-K–Grade 12, for ages 3–18. Recognition: GEMS Education network."
        ),
        "highlights": ["Innovation labs", "Arts", "Athletics"],
        "tags": ["AP", "American Curriculum", "Arts", "Co-ed", "Early Years", "Full Pathway", "GEMS Education", "Innovation Labs", "Premium (30-45k)", "Science Labs", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-german-international-school-doha",
        "title": "German International School Doha",
        "subtitle": "German Curriculum, Al Mamoura",
        "neighborhood": "Al Mamoura",
        "lat": 25.2419,
        "lng": 51.5008,
        "price_from_qar": 38000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "German-language education with international focus. Offers German Curriculum from Kindergarten–Grade 12, for ages 3–18. Recognition: German education system."
        ),
        "highlights": ["Language labs", "Sports", "Cultural facilities"],
        "tags": ["Co-ed", "Early Years", "Full Pathway", "German Curriculum", "Premium (30-45k)", "Science Labs", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-global-academy-international",
        "title": "Global Academy International",
        "subtitle": "American Curriculum, Doha",
        "neighborhood": "Doha",
        "lat": None,
        "lng": None,
        "price_from_qar": 18000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Multicultural American-style school. Offers American Curriculum from KG–Grade 12, for ages 3–18. Recognition: American curriculum."
        ),
        "highlights": ["Technology", "Sports", "Clubs"],
        "tags": ["American Curriculum", "Co-ed", "Early Years", "Full Pathway", "ICT & Technology", "Mid-Range (15-30k)", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-gulf-english-school",
        "title": "Gulf English School",
        "subtitle": "British Curriculum, Al Gharrafa",
        "neighborhood": "Al Gharrafa",
        "lat": 25.3339,
        "lng": 51.4408,
        "price_from_qar": 25000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Established British school. Offers British Curriculum from Foundation–Year 13, for ages 3–18. Recognition: British curriculum."
        ),
        "highlights": ["Science labs", "Sports", "Arts"],
        "tags": ["A Levels", "Arts", "British Curriculum", "Co-ed", "Early Years", "Full Pathway", "IGCSE", "Mid-Range (15-30k)", "Science Labs", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-hamilton-international-school",
        "title": "Hamilton International School",
        "subtitle": "British Curriculum, Lusail",
        "neighborhood": "Lusail",
        "lat": 25.43,
        "lng": 51.49,
        "price_from_qar": 36000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Modern premium British school. Offers British Curriculum from Pre-School–Year 13, for ages 3–18. Recognition: Nord Anglia Education."
        ),
        "highlights": ["STEAM", "Sports", "Performing arts"],
        "tags": ["A Levels", "Arts", "British Curriculum", "Co-ed", "Early Years", "Full Pathway", "IGCSE", "Nord Anglia", "Performing Arts", "Premium (30-45k)", "STEM & STEAM", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-hayat-universal-school",
        "title": "Hayat Universal School",
        "subtitle": "American Curriculum, Abu Hamour",
        "neighborhood": "Abu Hamour",
        "lat": 25.2286,
        "lng": 51.4869,
        "price_from_qar": 17000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Focus on academics and character development. Offers American Curriculum from KG–Grade 12, for ages 3–18. Recognition: American curriculum."
        ),
        "highlights": ["Labs", "Sports", "Technology"],
        "tags": ["American Curriculum", "Co-ed", "Early Years", "Full Pathway", "ICT & Technology", "Mid-Range (15-30k)", "Science Labs", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-international-school-of-choueifat-doha",
        "title": "International School of Choueifat – Doha",
        "subtitle": "SABIS® Curriculum, Abu Hamour",
        "neighborhood": "Abu Hamour",
        "lat": 25.2286,
        "lng": 51.4869,
        "price_from_qar": 26000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Structured international programme with global university preparation. Offers SABIS® Curriculum from KG–Grade 12, for ages 3–18. Recognition: SABIS® Network."
        ),
        "highlights": ["Science labs", "Sports facilities", "Libraries"],
        "tags": ["Co-ed", "Early Years", "Full Pathway", "Library", "Mid-Range (15-30k)", "SABIS", "SABIS Network", "Science Labs", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-international-school-london-qatar-isl-qatar",
        "title": "International School London Qatar (ISL Qatar)",
        "subtitle": "IB Curriculum, North Duhail",
        "neighborhood": "North Duhail",
        "lat": 25.3494,
        "lng": 51.4794,
        "price_from_qar": 47000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Offers IB PYP, MYP and Diploma Programme. Offers IB Curriculum from Early Years–Grade 12, for ages 3–18. Recognition: IB World School."
        ),
        "highlights": ["Innovation labs", "Arts", "Sports", "Library"],
        "tags": ["Arts", "Co-ed", "Early Years", "Elite (45k+)", "Full Pathway", "IB", "IB Diploma", "IB World School", "Innovation Labs", "Library", "Science Labs", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-japan-school-of-doha",
        "title": "Japan School of Doha",
        "subtitle": "Japanese National Curriculum, Doha",
        "neighborhood": "Doha",
        "lat": None,
        "lng": None,
        "price_from_qar": 25000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Serves Japanese families and follows Japan’s curriculum. Offers Japanese National Curriculum from Kindergarten–Junior High, for ages 3–15. Recognition: Japanese Ministry of Education system."
        ),
        "highlights": ["Japanese classrooms", "Sports facilities"],
        "tags": ["Co-ed", "Early Years", "Full Pathway", "Japanese Curriculum", "Mid-Range (15-30k)", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-kings-college-doha",
        "title": "King’s College Doha",
        "subtitle": "British Curriculum, Al Thumama",
        "neighborhood": "Al Thumama",
        "lat": 25.2378,
        "lng": 51.5308,
        "price_from_qar": 39000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Inspired by King’s College UK traditions. Offers British Curriculum from Pre-School–Year 13, for ages 3–18. Recognition: British curriculum."
        ),
        "highlights": ["Performing arts", "Sports", "Science facilities"],
        "tags": ["A Levels", "Arts", "British Curriculum", "Co-ed", "Early Years", "Full Pathway", "IGCSE", "Performing Arts", "Premium (30-45k)", "Science Labs", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-lebanese-school-qatar",
        "title": "Lebanese School Qatar",
        "subtitle": "Lebanese Curriculum / International pathway, Doha",
        "neighborhood": "Doha",
        "lat": None,
        "lng": None,
        "price_from_qar": 15000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Bilingual education environment. Offers Lebanese Curriculum / International pathway from KG–Grade 12, for ages 3–18. Recognition: Lebanese education system."
        ),
        "highlights": ["Labs", "Sports", "Cultural facilities"],
        "tags": ["Bilingual Arabic-English", "Co-ed", "Early Years", "Full Pathway", "Lebanese Curriculum", "Mid-Range (15-30k)", "Science Labs", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-loyola-international-school",
        "title": "Loyola International School",
        "subtitle": "CBSE, Al Wukair",
        "neighborhood": "Al Wukair",
        "lat": 25.14,
        "lng": 51.535,
        "price_from_qar": 15000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Indian curriculum school. Offers CBSE from KG–Grade 12, for ages 3–18. Recognition: CBSE affiliated."
        ),
        "highlights": ["Science labs", "Sports", "ICT"],
        "tags": ["CBSE", "CBSE Affiliated", "Co-ed", "Early Years", "Full Pathway", "ICT & Technology", "Mid-Range (15-30k)", "Science Labs", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-lycee-bonaparte-doha",
        "title": "Lycée Bonaparte Doha",
        "subtitle": "French National Curriculum, West Bay",
        "neighborhood": "West Bay",
        "lat": 25.3212,
        "lng": 51.531,
        "price_from_qar": 32000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "French education leading to Baccalauréat. Offers French National Curriculum from Preschool–Terminale, for ages 3–18. Recognition: AEFE network."
        ),
        "highlights": ["Language labs", "Cultural facilities"],
        "tags": ["AEFE", "Baccalaureat", "Co-ed", "Early Years", "French Curriculum", "Full Pathway", "Premium (30-45k)", "Science Labs", "Secondary"],
    },
    {
        "slug": "schools-lycee-franco-qatarien-voltaire",
        "title": "Lycée Franco-Qatarien Voltaire",
        "subtitle": "French National Curriculum, Doha",
        "neighborhood": "Doha",
        "lat": None,
        "lng": None,
        "price_from_qar": 30000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "French bilingual international school. Offers French National Curriculum from Preschool–Terminale, for ages 3–18. Recognition: French Ministry of Education."
        ),
        "highlights": ["Modern classrooms", "Arts", "Sports"],
        "tags": ["Arts", "Baccalaureat", "Bilingual Arabic-English", "Co-ed", "Early Years", "French Curriculum", "Full Pathway", "Premium (30-45k)", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-mesaieed-international-school",
        "title": "Mesaieed International School",
        "subtitle": "British Curriculum, Mesaieed",
        "neighborhood": "Mesaieed",
        "lat": 24.9917,
        "lng": 51.55,
        "price_from_qar": 25000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Serves Mesaieed industrial community. Offers British Curriculum from Foundation–Year 13, for ages 3–18. Recognition: British curriculum."
        ),
        "highlights": ["Sports fields", "Labs", "Library"],
        "tags": ["A Levels", "British Curriculum", "Co-ed", "Community School", "Early Years", "Full Pathway", "IGCSE", "Library", "Mid-Range (15-30k)", "Science Labs", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-middle-east-international-school",
        "title": "Middle East International School",
        "subtitle": "American Curriculum, Doha",
        "neighborhood": "Doha",
        "lat": None,
        "lng": None,
        "price_from_qar": 19000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "American education pathway. Offers American Curriculum from KG–Grade 12, for ages 3–18. Recognition: American curriculum."
        ),
        "highlights": ["ICT", "Sports", "Activities"],
        "tags": ["American Curriculum", "Co-ed", "Early Years", "Full Pathway", "ICT & Technology", "Mid-Range (15-30k)", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-newton-british-academy-barwa-city",
        "title": "Newton British Academy – Barwa City",
        "subtitle": "British Curriculum, Barwa City",
        "neighborhood": "Barwa City",
        "lat": 25.2064,
        "lng": 51.4747,
        "price_from_qar": 27000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Part of Newton group of schools. Offers British Curriculum from EYFS–Year 13, for ages 3–18. Recognition: British curriculum."
        ),
        "highlights": ["Science labs", "Sports", "Technology"],
        "tags": ["A Levels", "British Curriculum", "Co-ed", "Early Years", "Full Pathway", "ICT & Technology", "IGCSE", "Mid-Range (15-30k)", "Science Labs", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-newton-international-academy",
        "title": "Newton International Academy",
        "subtitle": "British Curriculum, Barwa City",
        "neighborhood": "Barwa City",
        "lat": 25.2064,
        "lng": 51.4747,
        "price_from_qar": 24000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Offers English National Curriculum. Offers British Curriculum from EYFS–Year 13, for ages 3–18. Recognition: British curriculum."
        ),
        "highlights": ["ICT", "Activities", "Sports"],
        "tags": ["A Levels", "British Curriculum", "Co-ed", "Early Years", "Full Pathway", "ICT & Technology", "IGCSE", "Mid-Range (15-30k)", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-newton-international-school-lagoon",
        "title": "Newton International School – Lagoon",
        "subtitle": "British Curriculum, West Bay Lagoon",
        "neighborhood": "West Bay Lagoon",
        "lat": 25.3739,
        "lng": 51.5133,
        "price_from_qar": 23000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Newton group campus. Offers British Curriculum from EYFS–Year 13, for ages 3–18. Recognition: British curriculum."
        ),
        "highlights": ["Labs", "Sports", "Arts"],
        "tags": ["A Levels", "Arts", "British Curriculum", "Co-ed", "Early Years", "Full Pathway", "IGCSE", "Mid-Range (15-30k)", "Science Labs", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-newton-international-school-d-ring",
        "title": "Newton International School – D Ring",
        "subtitle": "British Curriculum, D Ring Road",
        "neighborhood": "D Ring Road",
        "lat": 25.25,
        "lng": 51.52,
        "price_from_qar": 22000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Newton group campus. Offers British Curriculum from EYFS–Year 13, for ages 3–18. Recognition: British curriculum."
        ),
        "highlights": ["ICT", "Sports", "Student support"],
        "tags": ["A Levels", "British Curriculum", "Co-ed", "Early Years", "Full Pathway", "ICT & Technology", "IGCSE", "Mid-Range (15-30k)", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-newton-international-school-west-bay",
        "title": "Newton International School – West Bay",
        "subtitle": "British Curriculum, West Bay",
        "neighborhood": "West Bay",
        "lat": 25.3212,
        "lng": 51.531,
        "price_from_qar": 25000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Serves central Doha families. Offers British Curriculum from EYFS–Year 13, for ages 3–18. Recognition: British curriculum."
        ),
        "highlights": ["Modern classrooms", "Activities"],
        "tags": ["A Levels", "British Curriculum", "Co-ed", "Early Years", "Full Pathway", "IGCSE", "Mid-Range (15-30k)", "Secondary"],
    },
    {
        "slug": "schools-noble-international-school",
        "title": "Noble International School",
        "subtitle": "CBSE, Doha",
        "neighborhood": "Doha",
        "lat": None,
        "lng": None,
        "price_from_qar": 14000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Indian curriculum school. Offers CBSE from KG–Grade 12, for ages 3–18. Recognition: CBSE affiliated."
        ),
        "highlights": ["Labs", "Sports", "Activities"],
        "tags": ["Budget (under 15k)", "CBSE", "CBSE Affiliated", "Co-ed", "Early Years", "Full Pathway", "Science Labs", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-nord-anglia-international-school-al-khor",
        "title": "Nord Anglia International School Al Khor",
        "subtitle": "British & IB, Al Khor",
        "neighborhood": "Al Khor",
        "lat": 25.684,
        "lng": 51.497,
        "price_from_qar": 38000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "International school serving northern Qatar. Offers British & IB from Early Years–Year 13, for ages 3–18. Recognition: Nord Anglia Education."
        ),
        "highlights": ["STEAM", "Sports", "Global learning"],
        "tags": ["A Levels", "British Curriculum", "Co-ed", "Early Years", "Full Pathway", "IB", "IB Diploma", "IGCSE", "Nord Anglia", "Premium (30-45k)", "STEM & STEAM", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-oryx-international-school",
        "title": "Oryx International School",
        "subtitle": "British Curriculum, Mesaimeer",
        "neighborhood": "Mesaimeer",
        "lat": 25.2231,
        "lng": 51.4886,
        "price_from_qar": 38000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Established in partnership with Qatar Airways. Offers British Curriculum from Early Years–Year 13, for ages 3–18. Recognition: British curriculum."
        ),
        "highlights": ["Sports facilities", "Science labs", "Arts", "Innovation spaces"],
        "tags": ["A Levels", "Arts", "British Curriculum", "Co-ed", "Early Years", "Full Pathway", "IGCSE", "Innovation Labs", "Premium (30-45k)", "Science Labs", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-olive-international-school",
        "title": "Olive International School",
        "subtitle": "CBSE, Doha",
        "neighborhood": "Doha",
        "lat": None,
        "lng": None,
        "price_from_qar": 6000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Affordable Indian curriculum option. Offers CBSE from KG–Grade 12, for ages 3–18. Recognition: CBSE affiliated."
        ),
        "highlights": ["Classrooms", "Labs", "Activities"],
        "tags": ["Budget (under 15k)", "CBSE", "CBSE Affiliated", "Co-ed", "Early Years", "Full Pathway", "Science Labs", "Secondary"],
    },
    {
        "slug": "schools-pakistan-international-school-qatar",
        "title": "Pakistan International School Qatar",
        "subtitle": "Pakistani Curriculum (FBISE), Doha",
        "neighborhood": "Doha",
        "lat": None,
        "lng": None,
        "price_from_qar": 10000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "One of Qatar’s oldest Pakistani schools. Offers Pakistani Curriculum (FBISE) from KG–Grade 12, for ages 3–18. Recognition: Federal Board of Intermediate and Secondary Education."
        ),
        "highlights": ["Labs", "Sports", "Library"],
        "tags": ["Budget (under 15k)", "Co-ed", "Early Years", "Full Pathway", "Library", "Pakistani Curriculum", "Science Labs", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-pak-shamaa-school",
        "title": "Pak Shamaa School",
        "subtitle": "Pakistani Curriculum, Doha",
        "neighborhood": "Doha",
        "lat": None,
        "lng": None,
        "price_from_qar": 10000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Community-focused Pakistani school. Offers Pakistani Curriculum from KG–Grade 12, for ages 3–18. Recognition: Pakistan curriculum."
        ),
        "highlights": ["Classrooms", "Activities"],
        "tags": ["Budget (under 15k)", "Co-ed", "Community School", "Early Years", "Full Pathway", "Pakistani Curriculum", "Secondary"],
    },
    {
        "slug": "schools-park-house-english-school",
        "title": "Park House English School",
        "subtitle": "British Curriculum, Mesaimeer",
        "neighborhood": "Mesaimeer",
        "lat": 25.2231,
        "lng": 51.4886,
        "price_from_qar": 34000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Established British independent school. Offers British Curriculum from Foundation–Year 13, for ages 3–18. Recognition: British curriculum."
        ),
        "highlights": ["Sports", "Music", "Drama", "Science facilities"],
        "tags": ["A Levels", "British Curriculum", "Co-ed", "Early Years", "Full Pathway", "IGCSE", "Performing Arts", "Premium (30-45k)", "Science Labs", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-pearling-season-international-school",
        "title": "Pearling Season International School",
        "subtitle": "British Curriculum, Doha",
        "neighborhood": "Doha",
        "lat": None,
        "lng": None,
        "price_from_qar": 17000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "British pathway school. Offers British Curriculum from KG–Year 13, for ages 3–18. Recognition: British curriculum."
        ),
        "highlights": ["ICT", "Sports", "Activities"],
        "tags": ["A Levels", "British Curriculum", "Co-ed", "Early Years", "Full Pathway", "ICT & Technology", "IGCSE", "Mid-Range (15-30k)", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-philippine-international-school-qatar",
        "title": "Philippine International School Qatar",
        "subtitle": "Philippine Curriculum, Abu Hamour",
        "neighborhood": "Abu Hamour",
        "lat": 25.2286,
        "lng": 51.4869,
        "price_from_qar": 14000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Serves Filipino community. Offers Philippine Curriculum from Kindergarten–Grade 12, for ages 4–18. Recognition: Philippine education system."
        ),
        "highlights": ["Labs", "Sports", "Cultural programmes"],
        "tags": ["Budget (under 15k)", "Co-ed", "Community School", "Early Years", "Full Pathway", "Philippine Curriculum", "Science Labs", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-podar-pearl-school",
        "title": "Podar Pearl School",
        "subtitle": "CBSE, Doha",
        "neighborhood": "Doha",
        "lat": None,
        "lng": None,
        "price_from_qar": 12000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Part of Podar Education network. Offers CBSE from KG–Grade 12, for ages 3–18. Recognition: CBSE affiliated."
        ),
        "highlights": ["Digital classrooms", "Labs", "Sports"],
        "tags": ["Budget (under 15k)", "CBSE", "CBSE Affiliated", "Co-ed", "Early Years", "Full Pathway", "ICT & Technology", "Podar Network", "Science Labs", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-qatar-academy-doha",
        "title": "Qatar Academy Doha",
        "subtitle": "IB Curriculum, Education City",
        "neighborhood": "Education City",
        "lat": 25.3153,
        "lng": 51.4361,
        "price_from_qar": 55000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Flagship Qatar Foundation school. Offers IB Curriculum from Pre-K–Grade 12, for ages 3–18. Recognition: IB World School."
        ),
        "highlights": ["Advanced facilities", "Sports", "Arts"],
        "tags": ["Arts", "Co-ed", "Early Years", "Elite (45k+)", "Full Pathway", "IB", "IB Diploma", "IB World School", "Qatar Foundation", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-qatar-academy-al-khor",
        "title": "Qatar Academy Al Khor",
        "subtitle": "IB Curriculum, Al Khor",
        "neighborhood": "Al Khor",
        "lat": 25.684,
        "lng": 51.497,
        "price_from_qar": 40000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Serves northern Qatar. Offers IB Curriculum from Pre-K–Grade 12, for ages 3–18. Recognition: IB World School."
        ),
        "highlights": ["Sports", "Technology", "Arts"],
        "tags": ["Arts", "Co-ed", "Early Years", "Full Pathway", "IB", "IB Diploma", "IB World School", "ICT & Technology", "Premium (30-45k)", "Qatar Foundation", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-qatar-academy-al-wakrah",
        "title": "Qatar Academy Al Wakrah",
        "subtitle": "IB Curriculum, Al Wakrah",
        "neighborhood": "Al Wakrah",
        "lat": 25.1659,
        "lng": 51.5988,
        "price_from_qar": 40000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Qatar Foundation school. Offers IB Curriculum from Pre-K–Grade 12, for ages 3–18. Recognition: IB World School."
        ),
        "highlights": ["Modern campus", "Bilingual facilities"],
        "tags": ["Bilingual Arabic-English", "Co-ed", "Early Years", "Full Pathway", "IB", "IB Diploma", "IB World School", "Premium (30-45k)", "Qatar Foundation", "Secondary"],
    },
    {
        "slug": "schools-qatar-academy-msheireb",
        "title": "Qatar Academy Msheireb",
        "subtitle": "IB Curriculum, Msheireb",
        "neighborhood": "Msheireb",
        "lat": 25.2886,
        "lng": 51.5253,
        "price_from_qar": 45000,
        "age_groups": ["3-5", "6-12"],
        "description": (
            "Urban Qatar Foundation campus. Offers IB Curriculum from Early Years–Primary, for ages 3–11. Recognition: IB World School."
        ),
        "highlights": ["Modern learning spaces"],
        "tags": ["Co-ed", "Early Years", "Elite (45k+)", "IB", "IB World School", "Primary Only", "Qatar Foundation"],
    },
    {
        "slug": "schools-qatar-academy-sidra",
        "title": "Qatar Academy Sidra",
        "subtitle": "IB Curriculum, Education City",
        "neighborhood": "Education City",
        "lat": 25.3153,
        "lng": 51.4361,
        "price_from_qar": 50000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Qatar Foundation campus. Offers IB Curriculum from Early Years–Grade 12, for ages 3–18. Recognition: IB World School."
        ),
        "highlights": ["Sports", "Technology", "Arts"],
        "tags": ["Arts", "Co-ed", "Early Years", "Elite (45k+)", "Full Pathway", "IB", "IB Diploma", "IB World School", "ICT & Technology", "Qatar Foundation", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-qatar-canadian-school",
        "title": "Qatar Canadian School",
        "subtitle": "Canadian Curriculum (Alberta), Doha",
        "neighborhood": "Doha",
        "lat": None,
        "lng": None,
        "price_from_qar": 28000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Canadian education pathway. Offers Canadian Curriculum (Alberta) from KG–Grade 12, for ages 3–18. Recognition: Alberta curriculum."
        ),
        "highlights": ["STEM", "Sports", "Libraries"],
        "tags": ["Canadian Curriculum", "Co-ed", "Early Years", "Full Pathway", "Library", "Mid-Range (15-30k)", "STEM & STEAM", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-qatar-international-school",
        "title": "Qatar International School",
        "subtitle": "British Curriculum, Al Dafna",
        "neighborhood": "Al Dafna",
        "lat": 25.3172,
        "lng": 51.5289,
        "price_from_qar": 30000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "One of Doha’s oldest British schools. Offers British Curriculum from EYFS–Year 13, for ages 3–18. Recognition: British curriculum."
        ),
        "highlights": ["Sports", "Labs", "Performing arts"],
        "tags": ["A Levels", "Arts", "British Curriculum", "Co-ed", "Early Years", "Full Pathway", "IGCSE", "Performing Arts", "Premium (30-45k)", "Science Labs", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-qatar-turkish-school",
        "title": "Qatar Turkish School",
        "subtitle": "Turkish Curriculum, Ain Khaled",
        "neighborhood": "Ain Khaled",
        "lat": 25.2244,
        "lng": 51.4525,
        "price_from_qar": 15000,
        "age_groups": ["6-12", "13-18"],
        "description": (
            "Turkish national curriculum. Offers Turkish Curriculum from Primary–Secondary, for ages 6–18. Recognition: Turkish Ministry of Education."
        ),
        "highlights": ["Language facilities", "Cultural activities"],
        "tags": ["Co-ed", "Mid-Range (15-30k)", "Secondary", "Turkish Curriculum"],
    },
    {
        "slug": "schools-royal-grammar-school-guildford-qatar",
        "title": "Royal Grammar School Guildford Qatar",
        "subtitle": "British Curriculum, Al Mashaf",
        "neighborhood": "Al Mashaf",
        "lat": 25.155,
        "lng": 51.48,
        "price_from_qar": 42000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Inspired by RGS Guildford UK. Offers British Curriculum from Pre-School–Year 13, for ages 3–18. Recognition: British curriculum."
        ),
        "highlights": ["Premium sports", "Arts", "Science facilities"],
        "tags": ["A Levels", "Arts", "British Curriculum", "Co-ed", "Early Years", "Full Pathway", "IGCSE", "Premium (30-45k)", "Science Labs", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-sek-international-school-qatar",
        "title": "SEK International School Qatar",
        "subtitle": "IB Curriculum, West Bay",
        "neighborhood": "West Bay",
        "lat": 25.3212,
        "lng": 51.531,
        "price_from_qar": 46000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Full IB continuum. Offers IB Curriculum from Pre-School–Grade 12, for ages 3–18. Recognition: IB World School."
        ),
        "highlights": ["Innovation labs", "Sports", "Multilingual facilities"],
        "tags": ["Co-ed", "Early Years", "Elite (45k+)", "Full Pathway", "IB", "IB Diploma", "IB World School", "Innovation Labs", "Multilingual", "Science Labs", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-sherborne-qatar-preparatory-school",
        "title": "Sherborne Qatar – Preparatory School",
        "subtitle": "British Curriculum, Bani Hajer",
        "neighborhood": "Bani Hajer",
        "lat": 25.32,
        "lng": 51.39,
        "price_from_qar": 36000,
        "age_groups": ["3-5", "6-12"],
        "description": (
            "Preparatory campus. Offers British Curriculum from Pre-School–Year 6, for ages 3–11. Recognition: British curriculum."
        ),
        "highlights": ["Sports", "Arts", "Outdoor learning"],
        "tags": ["Arts", "British Curriculum", "Co-ed", "Early Years", "Outdoor Learning", "Premium (30-45k)", "Primary Only", "Sports Facilities"],
    },
    {
        "slug": "schools-sherborne-qatar-boys-school",
        "title": "Sherborne Qatar – Boys School",
        "subtitle": "British Curriculum, Al Rayyan",
        "neighborhood": "Al Rayyan",
        "lat": 25.2919,
        "lng": 51.4244,
        "price_from_qar": 38000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Boys’ senior school. Offers British Curriculum from Pre-School–Year 13, for ages 3–18. Recognition: British curriculum."
        ),
        "highlights": ["Sports", "Leadership", "Academics"],
        "tags": ["A Levels", "Boys Only", "British Curriculum", "Early Years", "Full Pathway", "IGCSE", "Premium (30-45k)", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-sherborne-qatar-girls-school",
        "title": "Sherborne Qatar – Girls School",
        "subtitle": "British Curriculum, Ain Khaled",
        "neighborhood": "Ain Khaled",
        "lat": 25.2244,
        "lng": 51.4525,
        "price_from_qar": 38000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Girls’ senior school. Offers British Curriculum from Pre-School–Year 13, for ages 3–18. Recognition: British curriculum."
        ),
        "highlights": ["Arts", "Sports", "Leadership"],
        "tags": ["A Levels", "Arts", "British Curriculum", "Early Years", "Full Pathway", "Girls Only", "IGCSE", "Premium (30-45k)", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-shantiniketan-indian-school",
        "title": "Shantiniketan Indian School",
        "subtitle": "CBSE, Doha",
        "neighborhood": "Doha",
        "lat": None,
        "lng": None,
        "price_from_qar": 10000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Indian curriculum school. Offers CBSE from KG–Grade 12, for ages 3–18. Recognition: CBSE affiliated."
        ),
        "highlights": ["Labs", "Sports", "Activities"],
        "tags": ["Budget (under 15k)", "CBSE", "CBSE Affiliated", "Co-ed", "Early Years", "Full Pathway", "Science Labs", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-spectra-global-school",
        "title": "Spectra Global School",
        "subtitle": "British / Cambridge Primary, Doha",
        "neighborhood": "Doha",
        "lat": None,
        "lng": None,
        "price_from_qar": 21000,
        "age_groups": ["3-5", "6-12"],
        "description": (
            "Primary-focused international school. Offers British / Cambridge Primary from Kindergarten–Primary, for ages 3–11. Recognition: Cambridge pathway."
        ),
        "highlights": ["ICT", "Science", "Sports"],
        "tags": ["British Curriculum", "Cambridge", "Cambridge International", "Co-ed", "Early Years", "ICT & Technology", "Mid-Range (15-30k)", "Primary Only", "Science Labs", "Sports Facilities"],
    },
    {
        "slug": "schools-stafford-sri-lankan-school-doha",
        "title": "Stafford Sri Lankan School Doha",
        "subtitle": "Sri Lankan Curriculum, Doha",
        "neighborhood": "Doha",
        "lat": None,
        "lng": None,
        "price_from_qar": 10000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Sri Lankan community school. Offers Sri Lankan Curriculum from Nursery–Grade 13, for ages 3–18. Recognition: Sri Lankan education system."
        ),
        "highlights": ["Labs", "Sports", "Cultural activities"],
        "tags": ["Budget (under 15k)", "Co-ed", "Community School", "Early Years", "Full Pathway", "Science Labs", "Secondary", "Sports Facilities", "Sri Lankan Curriculum"],
    },
    {
        "slug": "schools-swiss-international-school-qatar",
        "title": "Swiss International School Qatar",
        "subtitle": "IB Curriculum, Al Luqta",
        "neighborhood": "Al Luqta",
        "lat": 25.3236,
        "lng": 51.4602,
        "price_from_qar": 44000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "IB and multilingual education. Offers IB Curriculum from Pre-School–Grade 12, for ages 3–18. Recognition: IB World School."
        ),
        "highlights": ["Multilingual learning", "Sports", "Innovation"],
        "tags": ["Co-ed", "Early Years", "Full Pathway", "IB", "IB Diploma", "IB World School", "Innovation Labs", "Multilingual", "Premium (30-45k)", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-the-cambridge-school-doha",
        "title": "The Cambridge School Doha",
        "subtitle": "Cambridge / British, Doha",
        "neighborhood": "Doha",
        "lat": None,
        "lng": None,
        "price_from_qar": 18000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Cambridge examination pathway. Offers Cambridge / British from KG–Year 13, for ages 3–18. Recognition: Cambridge International."
        ),
        "highlights": ["Labs", "ICT", "Sports"],
        "tags": ["A Levels", "British Curriculum", "Cambridge", "Cambridge International", "Co-ed", "Early Years", "Full Pathway", "ICT & Technology", "IGCSE", "Mid-Range (15-30k)", "Science Labs", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-the-scholars-international-school",
        "title": "The Scholars International School",
        "subtitle": "British Curriculum, Doha",
        "neighborhood": "Doha",
        "lat": None,
        "lng": None,
        "price_from_qar": 20000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "British international school. Offers British Curriculum from KG–Year 13, for ages 3–18. Recognition: British curriculum."
        ),
        "highlights": ["Technology", "Activities", "Student support"],
        "tags": ["A Levels", "British Curriculum", "Co-ed", "Early Years", "Full Pathway", "ICT & Technology", "IGCSE", "Mid-Range (15-30k)", "Secondary"],
    },
    {
        "slug": "schools-united-school-international",
        "title": "United School International",
        "subtitle": "British Curriculum, The Pearl",
        "neighborhood": "The Pearl",
        "lat": 25.3697,
        "lng": 51.5508,
        "price_from_qar": 39000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "Premium school on The Pearl. Offers British Curriculum from Early Years–Year 13, for ages 3–18. Recognition: British curriculum."
        ),
        "highlights": ["STEAM", "Sports village", "Arts"],
        "tags": ["A Levels", "Arts", "British Curriculum", "Co-ed", "Early Years", "Full Pathway", "IGCSE", "Premium (30-45k)", "STEM & STEAM", "Secondary", "Sports Facilities"],
    },
    {
        "slug": "schools-vision-international-school",
        "title": "Vision International School",
        "subtitle": "American Curriculum, Al Waab",
        "neighborhood": "Al Waab",
        "lat": 25.2606,
        "lng": 51.4494,
        "price_from_qar": 27000,
        "age_groups": ["3-5", "6-12", "13-18"],
        "description": (
            "American pathway school. Offers American Curriculum from KG–Grade 12, for ages 3–18. Recognition: American curriculum."
        ),
        "highlights": ["STEM", "Sports", "Technology"],
        "tags": ["American Curriculum", "Co-ed", "Early Years", "Full Pathway", "ICT & Technology", "Mid-Range (15-30k)", "STEM & STEAM", "Secondary", "Sports Facilities"],
    },
)

assert len(SCHOOLS) == 84, f"Expected 84 schools, got {len(SCHOOLS)}"
