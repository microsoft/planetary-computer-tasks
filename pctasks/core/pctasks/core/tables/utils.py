import unicodedata

PROHIBITED_TABLE_KEY_CHARS = ["/", "\\", "#", "?"]


def is_valid_table_key(table_key: str) -> bool:
    for char in PROHIBITED_TABLE_KEY_CHARS:
        if char in table_key:
            return False
        if unicodedata.category(char)[0] == "C":
            return False
    return True
