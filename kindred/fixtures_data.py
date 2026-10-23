# Synthetic fixture data, hand-authored for offline development and tests. Not Qloo response data.
"""Hand-authored synthetic entities and tags for Kindred fixture transport."""

def _tag(id_, name):
    return {"id": id_, "name": name}

TAGS = [
    _tag("urn:tag:genre:media:indie", "indie"),
    _tag("urn:tag:genre:media:jazz", "jazz"),
    _tag("urn:tag:genre:media:neo_noir", "neo-noir"),
    _tag("urn:tag:genre:media:mystery", "mystery"),
    _tag("urn:tag:genre:media:romance", "romance"),
    _tag("urn:tag:genre:media:sci_fi", "sci-fi"),
    _tag("urn:tag:genre:media:punk", "punk"),
    _tag("urn:tag:genre:media:skate_punk", "skate punk"),
    _tag("urn:tag:genre:media:folk", "folk"),
    _tag("urn:tag:genre:media:lo_fi", "lo-fi"),
    _tag("urn:tag:mood:whimsical", "whimsical"),
    _tag("urn:tag:mood:melancholy", "melancholy"),
    _tag("urn:tag:mood:quiet", "quiet"),
    _tag("urn:tag:mood:cozy", "cozy"),
    _tag("urn:tag:mood:magical", "magical"),
    _tag("urn:tag:mood:energetic", "energetic"),
    _tag("urn:tag:mood:intense", "intense"),
    _tag("urn:tag:mood:dreamy", "dreamy"),
    _tag("urn:tag:mood:nostalgic", "nostalgic"),
    _tag("urn:tag:mood:heartwarming", "heartwarming"),
    _tag("urn:tag:mood:late_night", "late night"),
    _tag("urn:tag:theme:literary", "literary"),
    _tag("urn:tag:theme:surreal", "surreal"),
    _tag("urn:tag:theme:dystopian", "dystopian"),
    _tag("urn:tag:theme:diy", "diy"),
    _tag("urn:tag:cuisine:ramen", "ramen"),
    _tag("urn:tag:cuisine:natural_wine", "natural wine"),
    _tag("urn:tag:cuisine:bbq", "bbq"),
    _tag("urn:tag:cuisine:bakery", "bakery"),
    _tag("urn:tag:cuisine:tea", "tea"),
]

TAG_BY_ID = {t["id"]: t for t in TAGS}
TAG_BY_NAME = {t["name"].lower(): t for t in TAGS}

def T(*names):
    out = []
    for n in names:
        t = TAG_BY_NAME[n.lower()]
        out.append({"id": t["id"], "name": t["name"]})
    return out

_counter = [0]
def _eid():
    _counter[0] += 1
    return f"11111111-2222-4333-8444-{_counter[0]:012d}"

def _e(name, subtype, description, popularity, tags, properties=None, aliases=None):
    return {
        "id": _eid(),
        "name": name,
        "subtype": subtype,
        "description": description,
        "popularity": popularity,
        "tags": T(*tags),
        "properties": properties or {},
        "aliases": aliases or [],
    }

ENTITIES = [
    # movies
    _e("The Grand Budapest Hotel", "movie", "A whimsical hotel caper layered with melancholy and meticulous charm.", 0.92, ["indie", "whimsical", "melancholy", "cozy"], {"rating": 4.5}),
    _e("Amélie", "movie", "A whimsical Parisian fable about quiet kindness and small pleasures.", 0.90, ["indie", "whimsical", "melancholy", "romance", "quiet"], {"rating": 4.4}, aliases=["Amelie"]),
    _e("Spirited Away", "movie", "A magical bathhouse adventure about courage and growing up.", 0.94, ["indie", "magical", "whimsical", "cozy", "quiet"], {"rating": 4.8}),
    _e("Parasite", "movie", "A sharp, intense class thriller that twists into neo-noir territory.", 0.93, ["neo-noir", "intense", "mystery"], {"rating": 4.6}),
    _e("Whiplash", "movie", "An intense jazz-drumming duel between ambition and obsession.", 0.88, ["jazz", "intense", "energetic"], {"rating": 4.5}),
    _e("Mad Max: Fury Road", "movie", "A relentless dystopian road chase of pure kinetic energy.", 0.91, ["energetic", "intense", "dystopian"], {"rating": 4.3}),
    _e("Paddington 2", "movie", "A heartwarming, cozy caper with a very polite bear.", 0.85, ["heartwarming", "cozy", "whimsical"], {"rating": 4.2}),
    _e("Knives Out", "movie", "A playful mystery whodunit with neo-noir twists.", 0.89, ["mystery", "neo-noir", "whimsical"], {"rating": 4.1}),
    _e("La La Land", "movie", "A dreamy jazz romance about love and ambition in Los Angeles.", 0.87, ["jazz", "romance", "melancholy", "dreamy"], {"rating": 4.0}),
    _e("Dune", "movie", "A sweeping sci-fi epic of power, prophecy, and desert survival.", 0.95, ["sci-fi", "dystopian", "intense"], {"rating": 4.4}),
    # artists
    _e("Radiohead", "artist", "Experimental rock band blending indie melancholy with dreamy electronics.", 0.91, ["indie", "melancholy", "dreamy"]),
    _e("Phoebe Bridgers", "artist", "Indie singer-songwriter known for quiet, melancholy, whimsical songs.", 0.86, ["indie", "melancholy", "whimsical", "quiet", "folk"]),
    _e("Miles Davis", "artist", "Jazz pioneer whose cool, quiet late-night recordings reshaped music.", 0.90, ["jazz", "quiet", "late night", "cozy"]),
    _e("Nujabes", "artist", "Producer who fused jazz and lo-fi hip-hop into quiet, melancholy beats.", 0.84, ["jazz", "lo-fi", "quiet", "late night", "melancholy"]),
    _e("Fleetwood Mac", "artist", "Folk-rock legends with nostalgic, dreamy harmonies.", 0.92, ["folk", "nostalgic", "dreamy"]),
    _e("Khruangbin", "artist", "Dreamy, quiet groove trio drawing on global folk and funk.", 0.82, ["dreamy", "quiet", "folk"]),
    _e("The National", "artist", "Literary indie rock built on melancholy baritone and restless rhythms.", 0.83, ["indie", "melancholy", "literary"]),
    _e("Sufjan Stevens", "artist", "Whimsical, melancholy indie folk songwriter and arranger.", 0.85, ["indie", "folk", "whimsical", "melancholy"]),
    _e("Descendents", "artist", "Energetic skate punk pioneers with a fiercely DIY spirit.", 0.78, ["punk", "skate punk", "energetic", "diy"]),
    _e("Bad Religion", "artist", "Intense punk band known for fast, melodic, literate songs.", 0.80, ["punk", "skate punk", "intense"]),
    _e("NOFX", "artist", "Energetic skate punk band with a DIY streak and rapid-fire humour.", 0.79, ["punk", "skate punk", "energetic", "diy"]),
    _e("Rancid", "artist", "Energetic punk band rooted in skate punk and street-level storytelling.", 0.77, ["punk", "skate punk", "energetic"]),
    # books
    _e("Norwegian Wood", "book", "A quiet, melancholy literary novel about love and loss in Tokyo.", 0.84, ["indie", "melancholy", "literary", "quiet", "romance"]),
    _e("Kitchen", "book", "A quiet, cozy literary novella about grief, food, and healing.", 0.78, ["quiet", "cozy", "melancholy", "literary"]),
    _e("The Master and Margarita", "book", "A surreal, magical literary classic where the devil visits Moscow.", 0.82, ["literary", "surreal", "magical", "mystery"]),
    _e("Piranesi", "book", "A magical, quiet literary mystery set in an endless house of statues.", 0.80, ["magical", "quiet", "literary", "surreal"]),
    _e("Klara and the Sun", "book", "A melancholy sci-fi literary novel told by a devoted robot companion.", 0.83, ["sci-fi", "melancholy", "literary", "quiet"]),
    _e("The Left Hand of Darkness", "book", "A literary sci-fi classic about diplomacy on a frozen dystopian world.", 0.81, ["sci-fi", "literary", "dystopian"]),
    _e("Convenience Store Woman", "book", "A quiet, whimsical indie literary novel about finding your own rhythm.", 0.79, ["indie", "quiet", "whimsical", "literary"]),
    _e("A Gentleman in Moscow", "book", "A cozy, heartwarming literary novel set inside a grand hotel.", 0.86, ["cozy", "literary", "heartwarming", "nostalgic"]),
    # podcasts
    _e("Song Exploder", "podcast", "Musicians break down one song at a time, layer by layer.", 0.81, ["indie", "literary", "quiet"]),
    _e("99% Invisible", "podcast", "A quiet, literary look at the unnoticed design of everyday life.", 0.83, ["literary", "quiet", "cozy"]),
    _e("Heavyweight", "podcast", "Heartwarming, melancholy stories revisiting moments that still weigh on people.", 0.79, ["melancholy", "heartwarming", "cozy"]),
    _e("Criminal", "podcast", "A mystery podcast telling true stories of crime with neo-noir care.", 0.80, ["mystery", "neo-noir", "quiet"]),
    _e("Normal Gossip", "podcast", "Whimsical, cozy storytelling about gloriously low-stakes gossip.", 0.77, ["whimsical", "cozy", "heartwarming"]),
    # places - invented names only
    _e("Juniper & Rye", "place", "A natural wine bar pouring small-producer bottles in a quiet, whimsical room.", 0.82, ["natural wine", "indie", "whimsical", "melancholy", "quiet"], {"price_level": 3, "locality": "Portland", "address": "214 Juniper Lane, Portland"}),
    _e("Fern Hollow Kitchen", "place", "A cozy, quiet kitchen serving seasonal plates in a fern-filled dining room.", 0.78, ["cozy", "quiet"], {"price_level": 2, "locality": "Portland", "address": "88 Fern Hollow Rd, Portland"}),
    _e("Menya Midnight", "place", "A late-night ramen counter with punk playlists and a DIY, energetic spirit.", 0.84, ["ramen", "punk", "skate punk", "late night", "energetic", "diy"], {"price_level": 1, "locality": "Portland", "address": "12 Midnight Alley, Portland"}),
    _e("Golden Hour Oyster Bar", "place", "A dreamy oyster bar for natural wine, romance, and sunset shellfish.", 0.85, ["natural wine", "dreamy", "romance"], {"price_level": 4, "locality": "Austin", "address": "500 Golden Hour Blvd, Austin"}),
    _e("Little Fern Bakery", "place", "A whimsical, cozy bakery known for heartwarming morning pastries.", 0.76, ["bakery", "cozy", "whimsical", "heartwarming"], {"price_level": 1, "locality": "Portland", "address": "31 Little Fern St, Portland"}),
    _e("Smoke Signal BBQ", "place", "An energetic barbecue joint with nostalgic folk tunes and smoked brisket.", 0.81, ["bbq", "energetic", "folk", "nostalgic"], {"price_level": 2, "locality": "Austin", "address": "770 Smoke Signal Dr, Austin"}),
    _e("The Quiet Cup", "place", "A quiet tea house for literary afternoons and melancholy, cozy evenings.", 0.77, ["tea", "quiet", "cozy", "literary", "melancholy"], {"price_level": 1, "locality": "Austin", "address": "9 Quiet Cup Lane, Austin"}),
    _e("Nonna's Counter", "place", "A cozy, heartwarming counter serving nostalgic handmade pasta.", 0.80, ["cozy", "heartwarming", "nostalgic"], {"price_level": 2, "locality": "Austin", "address": "402 Nonna Way, Austin"}),
]

# remove internal counter side effects for determinism on reimport are fine
ENTITY_BY_ID = {e["id"]: e for e in ENTITIES}
