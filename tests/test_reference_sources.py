from app.services.reference_sources import load_reference_sources, reference_source_name


def test_default_reference_sources_contains_dataroma():
    urls = load_reference_sources()
    assert "https://www.dataroma.com/m/home.php/" in urls


def test_reference_source_name_for_dataroma():
    assert reference_source_name("https://www.dataroma.com/m/home.php") == "dataroma"
