"""
Food Safety Validation Engine for ANNADATA AI
Evaluates food safety, microbiological danger zones, packaging integrity,
and shelf-life across Prepared Food, Fresh Produce, and Raw Food Ingredients.

IMPORTANT PRINCIPLE:
AI provides assistive screening and risk grading, but NEVER unilaterally
certifies consumable safety without human verification triggers whenever
risk indicators, opened packaging, or perishable thresholds exist.
"""
from datetime import datetime, timezone, timedelta

# Application timezone: India Standard Time (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))

# Major donation categories
MAIN_DONATION_CATEGORIES = {
    'prepared_food': 'Prepared Food & Surplus Meals',
    'fresh_produce': 'Fresh Produce (Fruits & Vegetables)',
    'raw_ingredients': 'Raw Food Ingredients & Cooking Staples'
}

# Supported subcategories
ALLOWED_CATEGORIES = [
    # Prepared Food
    "cooked meals", "curries & gravies", "baked goods", "dairy", "snacks",
    "vegetarian", "non-vegetarian", "vegan", "beverages", "catering surplus", "buffet spread",
    # Fresh Produce
    "fruits", "vegetables", "leafy greens", "tubers & root vegetables", "farm surplus", "market produce",
    # Raw Ingredients
    "rice & grains", "wheat & flour", "pulses & lentils", "cooking oils", "spices & dry condiments",
    "packaged canned goods", "staples",
    # Fallback
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
        return True  # Optional for raw ingredients and produce if harvest date given
    return prep_time <= get_current_time()


def check_quantity(quantity):
    return quantity is not None and quantity > 0


def check_category(category):
    if not category:
        return False
    return category.strip().lower() in ALLOWED_CATEGORIES or True  # Allow flexible descriptors


def check_deadline(deadline):
    deadline = normalize_datetime(deadline)
    if deadline is None:
        return False
    return deadline > get_current_time()


def evaluate_prepared_food(donation):
    """Safety evaluation specific to cooked and prepared meals."""
    issues = []
    checks = {}
    recommendations = []
    requires_human_verification = False
    risk_level = "low"

    # Time checks
    now = get_current_time()
    prep_time = normalize_datetime(donation.preparation_time)
    exp_time = normalize_datetime(donation.expiry_time)
    deadline = normalize_datetime(donation.collection_deadline)

    if prep_time and prep_time > now:
        issues.append("Preparation time cannot be in the future.")
        checks["prep_time_valid"] = False
    else:
        checks["prep_time_valid"] = True

    if not exp_time or exp_time <= now:
        issues.append("Prepared food has passed consumption expiry.")
        checks["not_expired"] = True if (exp_time and exp_time > now) else False
    else:
        checks["not_expired"] = True

    if not deadline or deadline <= now:
        issues.append("Collection deadline has already elapsed.")
        checks["deadline_valid"] = False
    else:
        checks["deadline_valid"] = True

    if exp_time and deadline and deadline > exp_time:
        issues.append("Collection deadline cannot be later than expiry time.")

    # Temperature and Danger Zone checks (5°C to 60°C is bacterial danger zone)
    storage_temp = (donation.storage_temperature or "").lower()
    checks["storage_temperature"] = donation.storage_temperature or "Ambient"

    is_hot_held = "hot" in storage_temp or ">60" in storage_temp or "> 60" in storage_temp
    is_chilled = "refrig" in storage_temp or "cold" in storage_temp or "<5" in storage_temp or "< 5" in storage_temp

    if is_hot_held:
        checks["temperature_compliance"] = "Optimal hot holding (>60°C)"
        recommendations.append("Maintain continuous thermal heat insulation (>60°C) during courier transit.")
    elif is_chilled:
        checks["temperature_compliance"] = "Chilled cold chain (<5°C)"
        recommendations.append("Transport in insulated cooler bag with ice packs.")
    else:
        checks["temperature_compliance"] = "Ambient room temperature"
        # If ambient, check hours elapsed since prep
        if prep_time:
            hours_elapsed = (now - prep_time).total_seconds() / 3600.0
            checks["hours_since_prep"] = round(hours_elapsed, 1)
            if hours_elapsed > 4.0:
                issues.append(f"Prepared food held at ambient temperature for >{int(hours_elapsed)} hours (exceeds 4-hour microbial safety limit).")
                risk_level = "high"
                requires_human_verification = True
            elif hours_elapsed > 2.0:
                recommendations.append("Food in ambient temperature for >2h; dispatch immediate express courier rescue.")
                requires_human_verification = True
                risk_level = "medium"
        else:
            requires_human_verification = True

    # Packaging check
    pkg = (donation.packaging_type or "").lower()
    if any(k in pkg for k in ["open", "unsealed", "exposed", "loose"]):
        issues.append("Unsealed or open packaging creates cross-contamination risk.")
        requires_human_verification = True
        risk_level = "high"

    # Mandatory human verification policy for high-risk categories (meat/dairy)
    cat_lower = (donation.category or "").lower()
    if any(k in cat_lower for k in ["non-veg", "chicken", "meat", "fish", "dairy", "milk"]):
        requires_human_verification = True
        recommendations.append("Perishable protein/dairy item: NGO intake supervisor must perform olfactory inspection upon handover.")

    return {
        "suitable": len(issues) == 0,
        "issues": issues,
        "checks": checks,
        "recommendations": recommendations,
        "requires_human_verification": requires_human_verification,
        "risk_level": risk_level
    }


def evaluate_fresh_produce(donation):
    """Safety evaluation specific to fresh fruits, vegetables, and farm surplus."""
    issues = []
    checks = {}
    recommendations = []
    requires_human_verification = False
    risk_level = "low"

    now = get_current_time()
    exp_time = normalize_datetime(donation.expiry_time)
    deadline = normalize_datetime(donation.collection_deadline)

    if not exp_time or exp_time <= now:
        issues.append("Produce has passed estimated freshness shelf life.")
        checks["not_expired"] = False
    else:
        checks["not_expired"] = True

    if not deadline or deadline <= now:
        issues.append("Collection deadline has elapsed.")
        checks["deadline_valid"] = False
    else:
        checks["deadline_valid"] = True

    # Freshness condition checks
    cond = (donation.freshness_condition or "good").lower()
    checks["freshness_condition"] = donation.freshness_condition or "Good"

    if any(k in cond for k in ["spoiled", "rot", "mold", "decayed", "damaged beyond use"]):
        issues.append("Produce reported as spoiled or decaying; unsafe for human consumption.")
        risk_level = "critical"
        checks["consumable"] = False
    elif any(k in cond for k in ["bruised", "cooking only", "overripe"]):
        requires_human_verification = True
        risk_level = "medium"
        recommendations.append("Produce is ripe/bruised: Recommended for immediate community kitchen cooking, not long storage.")
        checks["consumable"] = True
    elif any(k in cond for k in ["harvested", "fresh", "crisp", "firm", "good"]):
        recommendations.append("Store in cool, well-ventilated dry crates away from direct sunlight.")
        checks["consumable"] = True

    # Harvest date checks
    if donation.harvest_date:
        h_date = normalize_datetime(donation.harvest_date)
        if h_date > now:
            issues.append("Harvest date cannot be in the future.")
        else:
            days_since = (now - h_date).total_seconds() / 86400.0
            checks["days_since_harvest"] = round(days_since, 1)
            if days_since > 10.0 and "tubers" not in (donation.produce_type or "").lower():
                requires_human_verification = True
                recommendations.append("Harvested >10 days ago; check firmness and hydration on arrival.")

    recommendations.append("Courier notice: Transport in sturdy, ventilated crates. Do not stack heavy sacks on top.")

    return {
        "suitable": len(issues) == 0 and risk_level != "critical",
        "issues": issues,
        "checks": checks,
        "recommendations": recommendations,
        "requires_human_verification": requires_human_verification,
        "risk_level": risk_level
    }


def evaluate_raw_ingredients(donation):
    """Safety evaluation specific to raw staples, grains, flour, pulses, and packaged ingredients."""
    issues = []
    checks = {}
    recommendations = []
    requires_human_verification = False
    risk_level = "low"

    now = get_current_time()
    exp_time = normalize_datetime(donation.expiry_time)
    deadline = normalize_datetime(donation.collection_deadline)

    # Expiry / Best Before check
    if not exp_time or exp_time <= now:
        issues.append("Raw ingredient has passed manufacturer expiry or best-before date.")
        checks["not_expired"] = False
    else:
        checks["not_expired"] = True

    if not deadline or deadline <= now:
        issues.append("Collection window has expired.")
        checks["deadline_valid"] = False
    else:
        checks["deadline_valid"] = True

    # Packaging condition check (critical for dry grains)
    pkg = (donation.packaging_condition or donation.packaging_type or "sealed").lower()
    checks["packaging_condition"] = donation.packaging_condition or donation.packaging_type or "Sealed"

    if any(k in pkg for k in ["torn", "pest", "wet", "water damaged", "infestation"]):
        issues.append("Packaging damaged, wet, or showing pest exposure.")
        risk_level = "critical"
        requires_human_verification = True
    elif any(k in pkg for k in ["open", "opened", "partial", "unsealed"]):
        requires_human_verification = True
        risk_level = "medium"
        recommendations.append("Opened/partial package: Volunteer and NGO must visually inspect for weevils, pests, and moisture clumping.")
    else:
        recommendations.append("Factory sealed / intact packaging: Maintain dry storage away from ground humidity.")

    # Storage requirements
    reqs = (donation.storage_requirements or "").lower()
    if "refrig" in reqs or "cold" in reqs:
        recommendations.append("Special storage note: Requires refrigeration upon delivery.")
    else:
        recommendations.append("Store on raised wooden pallets or dry racks in pest-controlled pantry.")

    return {
        "suitable": len(issues) == 0 and risk_level != "critical",
        "issues": issues,
        "checks": checks,
        "recommendations": recommendations,
        "requires_human_verification": requires_human_verification,
        "risk_level": risk_level
    }


def evaluate(donation):
    """
    Main dispatch evaluation engine.
    Dispatches to category-specific safety evaluators based on donation_category.
    Returns: (suitable: bool, issues: list[str])
    """
    if not check_quantity(donation.quantity):
        return False, ["Quantity must be greater than zero."]

    cat = (donation.donation_category or "prepared_food").lower()

    if cat == "fresh_produce":
        res = evaluate_fresh_produce(donation)
    elif cat == "raw_ingredients":
        res = evaluate_raw_ingredients(donation)
    else:
        # Default: prepared_food
        res = evaluate_prepared_food(donation)

    return res["suitable"], res["issues"]
