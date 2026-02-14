#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Suite de pruebas rápida para el módulo API-Futbol (modo manual).
- Evita caracteres no ASCII para no romper en cp1252/Windows.
- Permite parametrizar liga/temporada por CLI.
- Mantiene estilo print() para facilidad de lectura.
"""

import argparse
import sys
from api_football.api_client import APIFootballClient
from api_football.db_manager import DatabaseManager
from api_football.data_transformer import DataTransformer
from api_football.utils import setup_logger

logger = setup_logger(__name__)

ASCII_OK = "[OK]"
ASCII_FAIL = "[FAIL]"
ASCII_WARN = "[WARN]"


def test_api_connection(api_key: str | None = None) -> bool:
    print("\n" + "=" * 60)
    print("TEST 1: Conexión a API-Futbol")
    print("=" * 60)

    try:
        client = APIFootballClient(api_key)
        leagues = client.get_all_leagues()

        if leagues:
            print(f"{ASCII_OK} Conexión exitosa")
            print(f"{ASCII_OK} Total de ligas disponibles: {len(leagues)}")
            print("\nPrimeras 5 ligas:")
            for i, league in enumerate(leagues[:5], 1):
                print(f"  {i}. {league['country']['name']} - {league['league']['name']}")
            return True
        else:
            print(f"{ASCII_FAIL} No se pudieron obtener ligas")
            return False

    except Exception as e:
        print(f"{ASCII_FAIL} Error: {e}")
        return False


def test_database_connection() -> bool:
    print("\n" + "=" * 60)
    print("TEST 2: Conexión a MongoDB")
    print("=" * 60)

    try:
        db = DatabaseManager()
        if db.connect():
            print(f"{ASCII_OK} Conexión exitosa a MongoDB")

            stats = db.get_statistics()
            print(f"{ASCII_OK} Total partidos en BD: {stats.get('total_partidos', 0)}")
            print(f"{ASCII_OK} Total ligas en BD: {stats.get('total_ligas', 0)}")

            db.close()
            return True
        else:
            print(f"{ASCII_FAIL} No se pudo conectar a MongoDB")
            return False

    except Exception as e:
        print(f"{ASCII_FAIL} Error: {e}")
        return False


def test_single_league(league_id: int = 140, season: int = 2023, api_key: str | None = None) -> bool:
    print("\n" + "=" * 60)
    print(f"TEST 3: Procesamiento de una liga (ID: {league_id}, Season: {season})")
    print("=" * 60)

    try:
        api_client = APIFootballClient(api_key)
        db = DatabaseManager()

        if not db.connect():
            print(f"{ASCII_FAIL} No se pudo conectar a MongoDB")
            return False

        all_leagues = api_client.get_all_leagues()
        the_league = next((l for l in all_leagues if l['league']['id'] == league_id), None)

        if not the_league:
            print(f"{ASCII_FAIL} No se encontró la liga {league_id}")
            db.close()
            return False

        print(f"\n{ASCII_OK} Liga encontrada: {the_league['country']['name']} - {the_league['league']['name']}")

        print("\nObteniendo fixtures...")
        fixtures = api_client.get_fixtures_by_league(league_id, season)
        print(f"{ASCII_OK} Fixtures obtenidos: {len(fixtures)}")

        if not fixtures:
            print(f"{ASCII_WARN} No hay fixtures disponibles para esta liga")
            db.close()
            return True

        print("\nObteniendo clasificación...")
        standings = api_client.get_team_standings(league_id, season)
        print(f"{ASCII_OK} Equipos en clasificación: {len(standings)}")

        print("\nTransformando datos (primeros 5 fixtures)...")
        sample_fixtures = fixtures[:5]
        transformed = DataTransformer.batch_transform(sample_fixtures, the_league, standings)
        print(f"{ASCII_OK} Fixtures transformados: {len(transformed)}")

        if transformed:
            print("\n" + "-" * 60)
            print("EJEMPLO DE DATOS TRANSFORMADOS:")
            print("-" * 60)
            sample = transformed[0]
            print(f"Liga ID: {sample.get('liga_id')}")
            print(f"Fecha: {sample.get('fecha')} {sample.get('hora')}")
            print(f"Local: {sample.get('equipo_local')} (Pos: {sample.get('pos_clasif_local')})")
            print(f"Visitante: {sample.get('equipo_visitante')} (Pos: {sample.get('pos_clasif_visita')})")
            print(f"Resultado: {sample.get('goles_local_TR')} - {sample.get('goles_visitante_TR')}")
            print(f"Estado: {sample.get('estado_del_partido')}")
            print("-" * 60)

        print("\nInsertando en base de datos...")
        stats = db.insert_many_matches(transformed)
        print(f"{ASCII_OK} Insertados: {stats['insertados']}")
        print(f"{ASCII_OK} Actualizados: {stats.get('actualizados', 0)}")
        print(f"{ASCII_OK} Duplicados: {stats['duplicados']}")
        print(f"{ASCII_OK} Errores: {stats['errores']}")

        db.close()
        return True

    except Exception as e:
        print(f"{ASCII_FAIL} Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_transformation() -> bool:
    print("\n" + "=" * 60)
    print("TEST 4: Transformación de liga_id")
    print("=" * 60)

    test_cases = [
        ("Spain", "La Liga", "SPAIN_LA_LIGA"),
        ("England", "Premier League", "ENGLAND_PREMIER_LEAGUE"),
        ("France", "Ligue 1", "FRANCE_LIGUE_1"),
        ("Germany", "Bundesliga", "GERMANY_BUNDESLIGA"),
        ("Italy", "Serie A", "ITALY_SERIE_A"),
    ]

    all_passed = True

    for country, league, expected in test_cases:
        result = DataTransformer.transform_league_id(country, league)
        passed = result == expected
        symbol = ASCII_OK if passed else ASCII_FAIL

        print(f"{symbol} {country} - {league}")
        print(f"   Esperado: {expected}")
        print(f"   Obtenido: {result}")

        if not passed:
            all_passed = False

    return all_passed


def main() -> int:
    parser = argparse.ArgumentParser(description="Suite de pruebas rápida - API-Futbol")
    parser.add_argument("--league", type=int, default=140, help="ID de liga a probar (default: 140 - LaLiga)")
    parser.add_argument("--season", type=int, default=2023, help="Season a probar (default: 2023)")
    parser.add_argument("--api-key", type=str, default=None, help="API key (opcional; usa .env por defecto)")
    args = parser.parse_args()

    print("\n" + "#" * 60)
    print("# SUITE DE TESTS - MÓDULO API-FUTBOL")
    print("#" * 60)

    results = {
        "API Connection": test_api_connection(args.api_key),
        "Database Connection": test_database_connection(),
        "Data Transformation": test_data_transformation(),
        "Single League Processing": test_single_league(args.league, args.season, args.api_key),
    }

    # Resumen
    print("\n" + "#" * 60)
    print("# RESUMEN DE TESTS")
    print("#" * 60)

    total_passed = 0
    for test_name, result in results.items():
        symbol = ASCII_OK if result else ASCII_FAIL
        status = "PASSED" if result else "FAILED"
        print(f"{symbol} {test_name}: {status}")
        total_passed += int(bool(result))

    total_tests = len(results)
    print(f"\nTotal: {total_passed}/{total_tests} tests pasados")

    if total_passed == total_tests:
        print("\nOK Todos los tests pasaron exitosamente!")
        return 0
    else:
        print("\nWARN Algunos tests fallaron")
        return 1


if __name__ == "__main__":
    sys.exit(main())