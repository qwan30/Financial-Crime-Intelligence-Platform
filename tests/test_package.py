def test_package_exports_version() -> None:
    import fincrime

    assert fincrime.__version__ == "0.1.0"
