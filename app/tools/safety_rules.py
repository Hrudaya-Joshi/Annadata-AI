from datetime import datetime, timezone, timedelta

# Application timezone: India Standard Time (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))

ALLOWED_CATEGORIES = [
    "vegetarian",
    "non-vegetarian",
    "vegan",
    "beverages",
    "snacks",
    "dairy",
    "baked goods",
    "fruits",
    "cooked meals",
    "other"
]


def get_current_time():
    """Return the current time in IST as a timezone-aware datetime."""
    return datetime.now(IST)


def normalize_datetime(value):
    """Convert a datetime value into IST."""
    if value is None:
        return None

    if value.tzinfo is None:
        # Existing database values are treated as IST.
        return value.replace(tzinfo=IST)

    return value.astimezone(IST)


def check_expiry(expiry_time):
    expiry_time = normalize_datetime(expiry_time)

    if expiry_time is None:
        return False

    return expiry_time > get_current_time()


def check_prep_time(prep_time):
    prep_time = normalize_datetime(prep_time)

    if prep_time is None:
        return False

    return prep_time <= get_current_time()


def check_quantity(quantity):
    return quantity is not None and quantity > 0


def check_category(category):
    if not category:
        return False

    return category.strip().lower() in ALLOWED_CATEGORIES


def check_deadline(deadline):
    deadline = normalize_datetime(deadline)

    if deadline is None:
        return False

    return deadline > get_current_time()


def evaluate(donation):
    issues = []

    if not check_quantity(donation.quantity):
        issues.append("Quantity must be greater than zero.")

    if not check_category(donation.category):
        issues.append(
            f"Category '{donation.category}' is not in the allowed list."
        )

    if not check_expiry(donation.expiry_time):
        issues.append("Food is expired or expiry time is missing.")

    if not check_prep_time(donation.preparation_time):
        issues.append("Preparation time is in the future.")

    if not check_deadline(donation.collection_deadline):
        issues.append("Collection deadline has passed or is missing.")

    suitable = len(issues) == 0

    return suitable, issues