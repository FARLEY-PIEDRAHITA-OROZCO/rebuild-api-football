#!/usr/bin/env python3
"""Script principal para extraer datos de API-Futbol y almacenarlos en MongoDB."""
import argparse
import sys
from typing import Optional
from .api_client import APIFootballClient
from .data_transformer import DataTransformer
from .db_manager import DatabaseManager
from .utils import setup_logger

logger = setup_logger(__name__)


def process_league(
    api_client: APIFootballClient,
    db_manager: DatabaseManager,
    league_info: dict,
    season: int = 2023
) -> dict:
    """Procesa una liga específica: obtiene fixtures, transforma y guarda.
    
    Args:
        api_client: Cliente de la API
        db_manager: Gestor de base de datos
        league_info: Información de la liga
        season: Temporada a procesar (Free plan: 2021-2023)
        
    Returns:
        Diccionario con estadísticas del procesamiento
    """
    league_id = league_info['league']['id']
    league_name = league_info['league']['name']
    country_name = league_info['country']['name']
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Procesando: {country_name} - {league_name} (ID: {league_id})")
    logger.info(f"{'='*60}")
    
    stats = {
        'liga': league_name,
        'pais': country_name,
        'fixtures_obtenidos': 0,
        'fixtures_transformados': 0,
        'insertados': 0,
        'duplicados': 0,
        'errores': 0
    }
    
    try:
        # 1. Obtener clasificación de equipos
        logger.info("Obteniendo clasificación de equipos...")
        standings = api_client.get_team_standings(league_id, season)
        
        # 2. Obtener fixtures
        logger.info("Obteniendo partidos...")
        fixtures = api_client.get_fixtures_by_league(league_id, season)
        stats['fixtures_obtenidos'] = len(fixtures)
        
        if not fixtures:
            logger.warning(f"No se encontraron partidos para {league_name}")
            return stats
        
        # 3. Transformar datos
        logger.info("Transformando datos...")
        transformed_matches = DataTransformer.batch_transform(
            fixtures,
            league_info,
            standings
        )
        stats['fixtures_transformados'] = len(transformed_matches)
        
        # 4. Guardar en base de datos
        logger.info("Guardando en base de datos...")
        insert_stats = db_manager.insert_many_matches(transformed_matches)
        
        stats['insertados'] = insert_stats['insertados']
        stats['duplicados'] = insert_stats['duplicados']
        stats['errores'] = insert_stats['errores']
        
        logger.info(
            f"✓ Liga procesada: {stats['insertados']} nuevos, "
            f"{stats['duplicados']} duplicados"
        )
        
    except Exception as e:
        logger.error(f"Error procesando liga {league_name}: {str(e)}")
        stats['errores'] += 1
    
    return stats


def main(
    api_key: Optional[str] = None,
    limit_leagues: Optional[int] = None,
    season: int = 2023,
    specific_league_id: Optional[int] = None
) -> int:
    """Función principal del script.
    
    Args:
        api_key: API key de API-Futbol
        limit_leagues: Límite de ligas a procesar (para pruebas)
        season: Temporada a procesar (Free plan: 2021-2023)
        specific_league_id: ID específico de liga a procesar (opcional)
        
    Returns:
        Código de salida (0 = éxito, 1 = error)
    """
    logger.info("\n" + "="*80)
    logger.info("INICIO DE PROCESO - EXTRACCIÓN DE DATOS API-FUTBOL")
    logger.info("="*80 + "\n")
    
    try:
        # 1. Inicializar cliente API
        logger.info("Inicializando cliente API...")
        api_client = APIFootballClient(api_key)
        
        # 2. Inicializar gestor de base de datos
        logger.info("Conectando a MongoDB...")
        db_manager = DatabaseManager()
        
        if not db_manager.connect():
            logger.error("No se pudo conectar a MongoDB")
            return 1
        
        # 3. Obtener ligas
        if specific_league_id:
            logger.info(f"Modo específico: procesando solo liga ID {specific_league_id}")
            all_leagues = api_client.get_all_leagues()
            leagues = [l for l in all_leagues if l['league']['id'] == specific_league_id]
            
            if not leagues:
                logger.error(f"No se encontró liga con ID {specific_league_id}")
                return 1
        else:
            logger.info("Obteniendo todas las ligas disponibles...")
            leagues = api_client.get_all_leagues()
        
        if not leagues:
            logger.error("No se pudieron obtener ligas")
            return 1
        
        # Aplicar límite si se especificó
        if limit_leagues and limit_leagues > 0:
            logger.info(f"Limitando a {limit_leagues} ligas para pruebas")
            leagues = leagues[:limit_leagues]
        
        total_leagues = len(leagues)
        logger.info(f"\nTotal de ligas a procesar: {total_leagues}\n")
        
        # 4. Procesar cada liga
        all_stats = []
        
        for idx, league_info in enumerate(leagues, 1):
            logger.info(f"\nProcesando liga {idx}/{total_leagues}")
            
            stats = process_league(api_client, db_manager, league_info, season)
            all_stats.append(stats)
        
        # 5. Resumen final
        logger.info("\n" + "="*80)
        logger.info("RESUMEN FINAL")
        logger.info("="*80)
        
        total_fixtures = sum(s['fixtures_obtenidos'] for s in all_stats)
        total_insertados = sum(s['insertados'] for s in all_stats)
        total_duplicados = sum(s['duplicados'] for s in all_stats)
        total_errores = sum(s['errores'] for s in all_stats)
        
        logger.info(f"Ligas procesadas: {len(all_stats)}")
        logger.info(f"Total fixtures obtenidos: {total_fixtures}")
        logger.info(f"Total insertados en BD: {total_insertados}")
        logger.info(f"Total duplicados: {total_duplicados}")
        logger.info(f"Total errores: {total_errores}")
        
        # Obtener estadísticas de la BD
        logger.info("\nEstadísticas de la base de datos:")
        db_stats = db_manager.get_statistics()
        logger.info(f"Total partidos en BD: {db_stats.get('total_partidos', 0)}")
        logger.info(f"Total ligas en BD: {db_stats.get('total_ligas', 0)}")
        
        # Top 5 ligas con más partidos
        logger.info("\nTop 5 ligas con más partidos:")
        for idx, liga in enumerate(db_stats.get('partidos_por_liga', [])[:5], 1):
            logger.info(
                f"  {idx}. {liga.get('liga_nombre', 'N/A')} "
                f"({liga.get('_id', 'N/A')}): {liga.get('count', 0)} partidos"
            )
        
        logger.info("\n" + "="*80)
        logger.info("PROCESO COMPLETADO EXITOSAMENTE")
        logger.info("="*80 + "\n")
        
        # 6. Cerrar conexiones
        db_manager.close()
        
        return 0
        
    except KeyboardInterrupt:
        logger.warning("\n\nProceso interrumpido por el usuario")
        return 1
        
    except Exception as e:
        logger.error(f"\n\nError fatal: {str(e)}", exc_info=True)
        return 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Extrae datos de API-Futbol y los almacena en MongoDB'
    )
    
    parser.add_argument(
        '--api-key',
        type=str,
        help='API key de API-Futbol (opcional, se usa la del .env por defecto)'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        help='Limitar número de ligas a procesar (útil para pruebas)'
    )
    
    parser.add_argument(
        '--season',
        type=int,
        default=2023,
        help='Temporada a procesar (Free plan: 2021-2023, default: 2023)'
    )
    
    parser.add_argument(
        '--league-id',
        type=int,
        help='ID específico de liga a procesar (procesa solo esa liga)'
    )
    
    args = parser.parse_args()
    
    exit_code = main(
        api_key=args.api_key,
        limit_leagues=args.limit,
        season=args.season,
        specific_league_id=args.league_id
    )
    
    sys.exit(exit_code)
