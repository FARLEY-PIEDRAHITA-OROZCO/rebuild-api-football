import pytest
from api_football.data_transformer import DataTransformer

def test_transform_league_id_basic():
    cases = [
        ("Spain", "La Liga", "SPAIN_LA_LIGA"),
        ("England", "Premier League", "ENGLAND_PREMIER_LEAGUE"),
        ("France", "Ligue 1", "FRANCE_LIGUE_1"),
        ("Germany", "Bundesliga", "GERMANY_BUNDESLIGA"),
        ("Italy", "Serie A", "ITALY_SERIE_A"),
    ]
    for country, league, expected in cases:
        assert DataTransformer.transform_league_id(country, league) == expected

def test_infer_season_from_date():
    # Agosto o superior => temporada del mismo año
    assert DataTransformer.infer_season_from_date("2023-08-10", None) == 2023
    # Antes de agosto => temporada del año anterior
    assert DataTransformer.infer_season_from_date("2024-02-01", None) == 2023

def test_generate_season_id():
    out = DataTransformer.generate_season_id("SPAIN_LA_LIGA", 2023)
    assert out == "SPAIN_LA_LIGA_2023-24"

def test_generate_match_id_stable():
    mid = DataTransformer.generate_match_id(
        liga_id="SPAIN_LA_LIGA",
        season_year=2023,
        ronda="Regular Season - 1",
        equipo_local="Real Madrid",
        equipo_visitante="Barcelona",
        fecha="2023-09-01",
    )
    # Validamos patrón general sin exigir hash exacto
    assert mid.startswith("SPAIN_LA_LIGA_2023-24_J1_REA-BAR_20230901")