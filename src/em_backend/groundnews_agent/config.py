"""Configuration for the Ground News agent."""
from pathlib import Path

# Paths
AGENT_DIR = Path(__file__).parent
BACKEND_ROOT = AGENT_DIR.parent.parent.parent
FRONTEND_DATA_DIR = (
    BACKEND_ROOT.parent / "ElectOMate-Frontend" / "src" / "pages"
    / "HungaryDashboard" / "data" / "groundnews"
)
STORIES_FILE = FRONTEND_DATA_DIR / "stories.json"
OUTLETS_FILE = FRONTEND_DATA_DIR / "outlets.json"

# Claude via AWS Bedrock
CLAUDE_MODEL = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
CLAUDE_MAX_TOKENS = 4096
AWS_REGION = "us-west-2"

# Clustering
MIN_CLUSTER_SIZE = 2
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
BACKFILL_SIMILARITY_THRESHOLD = 0.72

# Fetching
MAX_ARTICLES_PER_FEED = 20
MAX_ARTICLE_AGE_DAYS = 7
FETCH_TIMEOUT_SECONDS = 15
MAX_CONCURRENT_DOWNLOADS = 6

# The 10 key election topics
ELECTION_TOPICS = [
    "war_peace",
    "eu_relations",
    "cost_of_living",
    "corruption",
    "migration",
    "family_policy",
    "energy_security",
    "democratic_standards",
    "euro_adoption",
    "cultural_issues",
]

TOPIC_KEYWORDS: dict[str, list[str]] = {
    "war_peace": ["ukraine", "russia", "war", "peace", "nato", "orosz", "ukrán", "háború", "béke"],
    "eu_relations": ["eu", "european union", "brussels", "sovereignty", "funds", "brüsszel", "szuverenitás"],
    "cost_of_living": ["inflation", "wages", "prices", "cost", "energy price", "infláció", "bérek", "árak", "rezsicsökkentés"],
    "corruption": ["corruption", "olaf", "fraud", "embezzlement", "korrupció", "csalás"],
    "migration": ["migration", "migrant", "border", "asylum", "bevándorlás", "migráns", "határ", "menekült"],
    "family_policy": ["family", "housing", "birth", "child", "csok", "család", "lakás", "gyermek"],
    "energy_security": ["gas", "oil", "nuclear", "paks", "energy", "gáz", "olaj", "atom", "energia"],
    "democratic_standards": ["media freedom", "judiciary", "rule of law", "press", "sajtószabadság", "jogállam", "bíróság"],
    "euro_adoption": ["euro", "eurozone", "forint", "currency", "euró", "eurózóna", "valuta"],
    "cultural_issues": ["gender", "lgbtq", "education", "ideology", "gender", "oktatás", "ideológia"],
}

# RSS feeds mapped to outlet IDs
RSS_FEEDS: dict[str, str] = {
    # Independent / Center
    "telex": "https://telex.hu/rss",
    "24hu": "https://24.hu/feed/",
    "444hu": "https://444.hu/feed",
    "hvg": "https://hvg.hu/rss",
    "portfolio": "https://www.portfolio.hu/rss/all.xml",
    "index": "https://index.hu/24ora/rss/",
    "valasz-online": "https://www.valaszonline.hu/feed/",
    "g7": "https://g7.hu/feed/",
    "magyar-hang": "https://magyarhang.org/feed/",
    "nepszava": "https://nepszava.hu/rss",
    "atlatszo": "https://atlatszo.hu/feed/",
    "direkt36": "https://www.direkt36.hu/feed/",
    "merce": "https://merce.hu/feed/",
    "magyar-narancs": "https://magyarnarancs.hu/rss",
    # Pro-government
    "origo": "https://www.origo.hu/contentpartner/rss/origo/origo.xml",
    "magyar-nemzet": "https://magyarnemzet.hu/feed/",
    "mandiner": "https://mandiner.hu/rss",
    "magyar-hirlap": "https://www.magyarhirlap.hu/rss",
    "pesti-sracok": "https://pestisracok.hu/feed/",
    "hungary-today": "https://hungarytoday.hu/feed/",
    "hungarian-conservative": "https://hungarianconservative.com/feed/",
    # State media
    "mti": "https://mti.hu/rss",
}
