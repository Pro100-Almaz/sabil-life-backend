"""Canonical seed records for Qatar entertainment venues.

Source: the "Entertainment" sheet of ``sabil-listing-data.xlsx``. Coordinates
come from the sheet's ``LatLen`` column; ``exact_address`` keeps the supplied
address or Plus Code. The sheet carries no prices, so ``price_from_qar`` is 0.

``contacts`` is an ordered tuple of ``(ListingContactType, value)`` pairs.
Phone numbers are normalised to ``+974 XXXX XXXX``; tracking query strings are
stripped from URLs.
"""

from apps.catalog.models import ListingCategory, ListingContactType

CATEGORY = ListingCategory.ENTERTAINMENT

PHONE = ListingContactType.PHONE
WEBSITE = ListingContactType.WEBSITE
INSTAGRAM = ListingContactType.INSTAGRAM

ENTERTAINMENT: tuple[dict, ...] = (
    {
        "slug": "entertainment-cineco-city-center",
        "title": "Cineco",
        "subtitle": "Cinema, City Center Doha",
        "neighborhood": "West Bay",
        "lat": 25.324688,
        "lng": 51.529013,
        "description": "Cinema complex at City Center Doha showing current films and "
        "family-friendly screenings.",
        "highlights": ["Cinema", "Family-friendly screenings"],
        "exact_address": "8GFH+VJC, Doha, Qatar",
        "contacts": (
            (PHONE, "+974 7719 1655"),
            (WEBSITE, "http://www.cinemaqatar.com/city-center-cinema/"),
        ),
    },
    {
        "slug": "entertainment-katara-cinema",
        "title": "Katara Cinema",
        "subtitle": "Cinema, Katara Cultural Village",
        "neighborhood": "Katara",
        "lat": 25.358746,
        "lng": 51.524946,
        "description": "Cinema venue in Katara Cultural Village offering a relaxed "
        "setting for film screenings.",
        "highlights": ["Cinema"],
        "exact_address": "Doha, Qatar",
        "contacts": (
            (PHONE, "+974 3139 3976"),
            (INSTAGRAM, "https://instagram.com/katara.cinema"),
        ),
    },
    {
        "slug": "entertainment-novo-cinemas-souq-waqif",
        "title": "Novo Cinemas Souq Waqif",
        "subtitle": "Cinema, Souq Waqif",
        "neighborhood": "Souq Waqif",
        "lat": 25.286663,
        "lng": 51.531938,
        "description": "Novo Cinemas branch in Souq Waqif, offering modern movie "
        "screenings in Doha’s historic market district.",
        "highlights": ["Cinema"],
        "exact_address": "7GPJ+MQ8 Souq waqif, Doha, Qatar",
        "contacts": (
            (PHONE, "+974 4426 0777"),
            (WEBSITE, "http://qa.novocinemas.com/"),
        ),
    },
    {
        "slug": "entertainment-novo-cinemas-the-pearl",
        "title": "Novo Cinemas, The Pearl",
        "subtitle": "Cinema, The Pearl-Qatar",
        "neighborhood": "The Pearl",
        "lat": 25.366248,
        "lng": 51.550126,
        "description": "Multiplex cinema in The Pearl-Qatar, showing current releases "
        "in a contemporary entertainment setting.",
        "highlights": ["Cinema", "Multiplex"],
        "exact_address": "Novo Cinemas The Pearl, Doha, Qatar",
        "contacts": (
            (PHONE, "+974 4426 0777"),
            (WEBSITE, "https://qa.novocinemas.com/"),
        ),
    },
    {
        "slug": "entertainment-flik-cinemas",
        "title": "Flik Cinemas",
        "subtitle": "Cinema, Doha",
        "neighborhood": "Doha",
        "lat": 25.272913,
        "lng": 51.503338,
        "description": "Doha cinema offering regular and premium movie-viewing "
        "experiences, including family-friendly options.",
        "highlights": ["Cinema", "Premium screens", "Family-friendly screenings"],
        "exact_address": "7GF3+589, Street, Doha, Qatar",
        "contacts": (
            (PHONE, "+974 4442 0838"),
            (WEBSITE, "https://www.flikcinemas.com/"),
        ),
    },
    {
        "slug": "entertainment-doha-oasis",
        "title": "Doha Oasis",
        "subtitle": "Leisure & retail destination, Msheireb",
        "neighborhood": "Msheireb",
        "lat": 25.285431,
        "lng": 51.519543,
        "description": "Mixed-use leisure and retail destination in central Doha, home "
        "to dining, shopping, cinema, and attractions.",
        "highlights": ["Dining", "Shopping", "Cinema", "Attractions"],
        "exact_address": "42 Al Khaleej, Doha, Qatar",
        "contacts": (
            (PHONE, "+974 4410 4100"),
            (WEBSITE, "https://www.dohaoasis.com/"),
        ),
    },
    {
        "slug": "entertainment-abdul-aziz-nasser-theatre",
        "title": "Abdul Aziz Nasser Theatre",
        "subtitle": "Performing-arts theatre, Souq Waqif",
        "neighborhood": "Souq Waqif",
        "lat": 25.286510,
        "lng": 51.534370,
        "description": "Performing-arts theatre in Souq Waqif hosting plays, concerts, "
        "cultural events, and other live shows.",
        "highlights": ["Theatre", "Concerts", "Cultural events"],
        "exact_address": "Banks Street, Doha, Qatar",
        "contacts": (
            (PHONE, "+974 4499 3092"),
            (WEBSITE, "https://www.antheatre.qa/"),
        ),
    },
    {
        "slug": "entertainment-katara-drama-theater",
        "title": "Katara Drama Theater",
        "subtitle": "Theatre, Katara Cultural Village",
        "neighborhood": "Katara",
        "lat": 25.359838,
        "lng": 51.524263,
        "description": "Katara Cultural Village theatre for drama productions, "
        "performances, festivals, and community events.",
        "highlights": ["Theatre", "Festivals", "Community events"],
        "exact_address": "9G5F+WPJ, Doha, Qatar",
        "contacts": ((WEBSITE, "https://katara.net/"),),
    },
    {
        "slug": "entertainment-katara-opera-house",
        "title": "Katara Opera House",
        "subtitle": "Opera house, Katara Cultural Village",
        "neighborhood": "Katara",
        "lat": 25.360023,
        "lng": 51.524733,
        "description": "Landmark Katara venue for concerts, cultural performances, "
        "theatre, and major live events.",
        "highlights": ["Concerts", "Theatre", "Live events"],
        "exact_address": "9G5F+XP6, Doha, Qatar",
        "contacts": ((PHONE, "+974 4454 8185"),),
    },
    {
        "slug": "entertainment-nerf-action-xperience",
        "title": "NERF Action Xperience",
        "subtitle": "Indoor action & adventure venue, Msheireb",
        "neighborhood": "Msheireb",
        "lat": 25.285313,
        "lng": 51.528563,
        "description": "Indoor action and adventure venue with NERF-themed challenges, "
        "obstacle courses, and group activities.",
        "highlights": ["Obstacle courses", "NERF challenges", "Group activities"],
        "exact_address": "7GPH+4C, Doha, Qatar",
        "contacts": (
            (PHONE, "+974 5995 3666"),
            (WEBSITE, "https://nerfaxqatar.com/xtreme-challenge-course-obstacles/"),
        ),
    },
    {
        "slug": "entertainment-adventure-rooms-qatar",
        "title": "Adventure Rooms Qatar",
        "subtitle": "Escape rooms, Doha",
        "neighborhood": "Doha",
        "lat": 25.254740,
        "lng": 51.514000,
        "description": "Live escape-room experience where groups solve themed puzzles "
        "and challenges within a time limit.",
        "highlights": ["Escape rooms", "Group activities"],
        "exact_address": "Building No. 51, Doha, Qatar",
        "contacts": (
            (PHONE, "+974 7050 0139"),
            (WEBSITE, "http://www.adventureroomsqa.com/"),
        ),
    },
    {
        "slug": "entertainment-battlezone-paintball",
        "title": "Battlezone Paintball",
        "subtitle": "Indoor paintball, Al Thumama Mall",
        "neighborhood": "Al Thumama",
        "lat": 25.220831,
        "lng": 51.542241,
        "description": "Indoor paintball arena at Al Thumama, providing supervised team "
        "games for groups and celebrations.",
        "highlights": ["Paintball", "Supervised team games", "Celebrations"],
        "exact_address": "Al Thumama Mall, Doha, Qatar",
        "contacts": (
            (PHONE, "+974 7741 0774"),
            (WEBSITE, "https://battlezoneqa.com/"),
        ),
    },
    {
        "slug": "entertainment-kidzania-doha",
        "title": "KidZania Doha",
        "subtitle": "Children’s role-play city, Aspire Park",
        "neighborhood": "Aspire Zone",
        "lat": 25.258275,
        "lng": 51.439100,
        "description": "Interactive children’s role-play city where young visitors "
        "explore jobs and real-world activities through play.",
        "highlights": ["Role-play", "Kids activities"],
        "exact_address": "Aspire Park, Doha, Qatar",
        "contacts": (
            (PHONE, "+974 4482 6222"),
            (WEBSITE, "https://doha.kidzania.com/en-qa"),
        ),
    },
    {
        "slug": "entertainment-new-city-entertainment",
        "title": "New city entertainment",
        "subtitle": "Indoor family entertainment, Al Thumama",
        "neighborhood": "Al Thumama",
        "lat": 25.220738,
        "lng": 51.543013,
        "description": "Indoor family entertainment venue in Doha offering leisure "
        "activities for children and groups.",
        "highlights": ["Indoor play", "Family-friendly"],
        "exact_address": "6GCV+76R, F Ring Rd, Doha, Qatar",
        "contacts": ((PHONE, "+974 6600 4616"),),
    },
    {
        "slug": "entertainment-yippyland",
        "title": "Yippyland Entertainment",
        "subtitle": "Children’s indoor entertainment, Muaither",
        "neighborhood": "Muaither",
        "lat": 25.266888,
        "lng": 51.415813,
        "description": "Children’s indoor entertainment center in Al Rayyan with rides, "
        "games, and family-friendly activities.",
        "highlights": ["Rides", "Games", "Family-friendly"],
        "exact_address": "7C88+Q84, Muaither N St, Al-Rayyan, Qatar",
        "contacts": (
            (PHONE, "+974 6647 2101"),
            (WEBSITE, "https://www.facebook.com/yippyland.qa/"),
        ),
    },
)
