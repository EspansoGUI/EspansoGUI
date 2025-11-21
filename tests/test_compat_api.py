def test_import_espansoapi_alias():
    from espansogui import EspansoAPI

    # Ensure EspansoAPI is importable and instantiable
    api = EspansoAPI()
    assert api is not None

    # Basic surface checks
    assert hasattr(api, "ping"), "API missing 'ping'"
    assert hasattr(api, "list_snippets"), "API missing 'list_snippets'"

    ping = api.ping()
    assert isinstance(ping, dict)
    assert "status" in ping

    snippets = api.list_snippets()
    assert isinstance(snippets, list)
