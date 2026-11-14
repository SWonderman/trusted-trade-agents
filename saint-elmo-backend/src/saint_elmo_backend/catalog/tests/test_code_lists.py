import pytest

from saint_elmo_backend.catalog import code_lists
from saint_elmo_backend.db.seeders.code_lists import CODE_LIST_MODELS


@pytest.mark.parametrize("list_name", list(CODE_LIST_MODELS))
def test_every_vendored_list_loads(list_name):
    entries = code_lists.load_code_list(list_name)

    assert entries
    assert all(e.code == code for code, e in entries.items())


@pytest.mark.parametrize(
    ("code", "name"),
    [
        ("AM", "Milk and its derivatives"),
        # The letters mislead: UN is shellfish, ML is lactose, BP is linalool
        ("UN", "Shellfish and its derivatives"),
        ("ML", "Lactose"),
        ("BP", "Linalool"),
        ("X99", "Does not contain declaration obligatory allergens"),
    ],
)
def test_allergen_names_follow_gs1(code, name):
    entry = code_lists.load_code_list(code_lists.ALLERGEN_TYPE)[code]

    assert entry.name == name
    assert entry.is_standard


def test_duplicate_codes_keep_first_entry():
    # CHOCAL is listed twice; the first entry has the fuller name
    entry = code_lists.load_code_list(code_lists.NUTRIENT_TYPE)["CHOCAL"]

    assert entry.name == "Cholecalciferol; vitamin D3"


def test_names_are_stripped():
    # The source has "Amylcinnamyl alcohol " with a trailing space
    entry = code_lists.load_code_list(code_lists.ALLERGEN_TYPE)["AA"]

    assert entry.name == "Amylcinnamyl alcohol"


def test_empty_gs1_name_is_filled_from_overrides():
    labels = code_lists.load_code_list(code_lists.PACKAGING_LABEL)

    assert labels["FINNISH_HEART_SYMBOL"].name == "Finnish Heart Symbol"
    assert labels["FINNISH_HEART_SYMBOL"].definition
    assert labels["FINNISH_HEART_SYMBOL"].is_standard


def test_derived_energy_codes_are_named_but_not_standard():
    nutrients = code_lists.load_code_list(code_lists.NUTRIENT_TYPE)

    assert nutrients["ENER-KJO"].name == "Energy (kilojoules)"
    assert not nutrients["ENER-KJO"].is_standard
    assert nutrients["ENER-"].is_standard
