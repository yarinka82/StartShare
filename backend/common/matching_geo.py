REGION_TO_COUNTRIES = {
    "dach": {"de", "at", "ch"},
    "eu": {"de", "at", "ch", "eu", "nl", "fr", "pl", "es", "it", "se", "ee", "be", "dk", "fi", "ie", "pt"},
    "europe": {"de", "at", "ch", "eu", "gb", "ua", "nl", "fr", "pl", "es", "it", "se", "ee", "be", "dk", "fi", "ie",
               "pt"},
    "worldwide": None,  # підходить будь-яка країна
}


def is_country_in_regions(startup_country_code: str, investor_regions: list[str]) -> bool:
    """Перевіряє, чи входить країна стартапу в хоча б один макро-регіон інвестора."""
    if "worldwide" in investor_regions:
        return True
    
    allowed_countries = set()
    for r in investor_regions:
        allowed_countries.update(REGION_TO_COUNTRIES.get(r, set()))
    
    return startup_country_code.lower() in allowed_countries