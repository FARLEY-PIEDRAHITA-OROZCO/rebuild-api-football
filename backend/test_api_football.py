    #!/usr/bin/env python3
"""Script de prueba rápida para el módulo API-Futbol."""

from api_football.api_client import APIFootballClient
from api_football.db_manager import DatabaseManager
from api_football.data_transformer import DataTransformer
from api_football.utils import setup_logger

logger = setup_logger(__name__)


def test_api_connection():
    """Prueba la conexión a la API."""
    print("\n" + "="*60)
    print("TEST 1: Conexión a API-Futbol")
    print("="*60)
    
    try:
        client = APIFootballClient()
        leagues = client.get_all_leagues()
        
        if leagues:
            print(f"✓ Conexión exitosa")
            print(f"✓ Total de ligas disponibles: {len(leagues)}")
            print(f"\nPrimeras 5 ligas:")
            for i, league in enumerate(leagues[:5], 1):
                print(f"  {i}. {league['country']['name']} - {league['league']['name']}")
            return True
        else:
            print("✗ No se pudieron obtener ligas")
            return False
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def test_database_connection():
    """Prueba la conexión a MongoDB."""
    print("\n" + "="*60)
    print("TEST 2: Conexión a MongoDB")
    print("="*60)
    
    try:
        db = DatabaseManager()
        if db.connect():
            print("✓ Conexión exitosa a MongoDB")
            
            # Verificar estadísticas
            stats = db.get_statistics()
            print(f"✓ Total partidos en BD: {stats.get('total_partidos', 0)}")
            print(f"✓ Total ligas en BD: {stats.get('total_ligas', 0)}")
            
            db.close()
            return True
        else:
            print("✗ No se pudo conectar a MongoDB")
            return False
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def test_single_league():
    """Prueba el procesamiento de una sola liga."""
    print("\n" + "="*60)
    print("TEST 3: Procesamiento de una liga (La Liga - ID: 140)")
    print("="*60)
    
    try:
        # Inicializar cliente y BD
        api_client = APIFootballClient()
        db = DatabaseManager()
        
        if not db.connect():
            print("✗ No se pudo conectar a MongoDB")
            return False
        
        # Obtener información de La Liga
        all_leagues = api_client.get_all_leagues()
        laliga = next((l for l in all_leagues if l['league']['id'] == 140), None)
        
        if not laliga:
            print("✗ No se encontró La Liga")
            return False
        
        print(f"\n✓ Liga encontrada: {laliga['country']['name']} - {laliga['league']['name']}")
        
        # Obtener fixtures
        print("\nObteniendo fixtures...")
        fixtures = api_client.get_fixtures_by_league(140, 2023)
        print(f"✓ Fixtures obtenidos: {len(fixtures)}")
        
        if not fixtures:
            print("⚠ No hay fixtures disponibles para esta liga")
            return True
        
        # Obtener clasificación
        print("\nObteniendo clasificación...")
        standings = api_client.get_team_standings(140, 2023)
        print(f"✓ Equipos en clasificación: {len(standings)}")
        
        # Transformar primeros 5 fixtures
        print("\nTransformando datos (primeros 5 fixtures)...")
        sample_fixtures = fixtures[:5]
        transformed = DataTransformer.batch_transform(sample_fixtures, laliga, standings)
        print(f"✓ Fixtures transformados: {len(transformed)}")
        
        # Mostrar ejemplo de datos transformados
        if transformed:
            print("\n" + "-"*60)
            print("EJEMPLO DE DATOS TRANSFORMADOS:")
            print("-"*60)
            sample = transformed[0]
            print(f"Liga ID: {sample['liga_id']}")
            print(f"Fecha: {sample['fecha']} {sample['hora']}")
            print(f"Local: {sample['equipo_local']} (Pos: {sample['pos_clasif_local']})")
            print(f"Visitante: {sample['equipo_visitante']} (Pos: {sample['pos_clasif_visita']})")
            print(f"Resultado: {sample['goles_local_TR']} - {sample['goles_visitante_TR']}")
            print(f"Estado: {sample['estado_del_partido']}")
            print("-"*60)
        
        # Insertar en BD
        print("\nInsertando en base de datos...")
        stats = db.insert_many_matches(transformed)
        print(f"✓ Insertados: {stats['insertados']}")
        print(f"✓ Duplicados: {stats['duplicados']}")
        print(f"✓ Errores: {stats['errores']}")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_data_transformation():
    """Prueba la transformación de liga_id."""
    print("\n" + "="*60)
    print("TEST 4: Transformación de liga_id")
    print("="*60)
    
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
        symbol = "✓" if passed else "✗"
        
        print(f"{symbol} {country} - {league}")
        print(f"   Esperado: {expected}")
        print(f"   Obtenido: {result}")
        
        if not passed:
            all_passed = False
    
    return all_passed


def main():
    """Ejecuta todos los tests."""
    print("\n" + "#"*60)
    print("# SUITE DE TESTS - MÓDULO API-FUTBOL")
    print("#"*60)
    
    results = {
        "API Connection": test_api_connection(),
        "Database Connection": test_database_connection(),
        "Data Transformation": test_data_transformation(),
        "Single League Processing": test_single_league(),
    }
    
    # Resumen
    print("\n" + "#"*60)
    print("# RESUMEN DE TESTS")
    print("#"*60)
    
    for test_name, result in results.items():
        symbol = "✓" if result else "✗"
        status = "PASSED" if result else "FAILED"
        print(f"{symbol} {test_name}: {status}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    
    print(f"\nTotal: {total_passed}/{total_tests} tests pasados")
    
    if total_passed == total_tests:
        print("\n✓ Todos los tests pasaron exitosamente!")
        return 0
    else:
        print("\n✗ Algunos tests fallaron")
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
