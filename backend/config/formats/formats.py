
# Overrides Django's built-in Ukrainian date formats, which default to
# something like "2 березня 2026 р." — not what we want for a registry.
#
# This affects: admin list_display columns, admin form widgets (both
# display and what the user can type in), and any {{ date|date }} template
# tag rendering, wherever LANGUAGE_CODE = 'uk' is active.

DATE_FORMAT = 'd.m.Y'          # e.g. 02.03.2026 — used in list_display, templates
SHORT_DATE_FORMAT = 'd.m.Y'    # short form, same result here

DATETIME_FORMAT = 'd.m.Y H:i'
SHORT_DATETIME_FORMAT = 'd.m.Y H:i'

DATE_INPUT_FORMATS = [
    '%d.%m.%Y',   # 02.03.2026  <- what the admin date widget will accept when typed
    '%d.%m.%y',   # 02.03.26
    '%Y-%m-%d',   # 2026-03-02  <- keep ISO working too, for API/DB compatibility
]