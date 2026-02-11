"""Transformador de datos de la API a formato requerido."""
from typing import Dict, List, Optional, Any
from datetime import datetime
from .utils import setup_logger, normalize_string

logger = setup_logger(__name__)


class DataTransformer:
    """Transforma datos de la API al formato requerido."""
    
    @staticmethod
    def transform_league_id(country: str, league_name: str) -> str:
        """Transforma el ID de liga al formato PAIS_NOMBRE-DE-LIGA.
        
        Args:
            country: Nombre del país
            league_name: Nombre de la liga
            
        Returns:
            ID de liga transformado (ej: SPAIN_LALIGA)
        """
        country_normalized = normalize_string(country)
        league_normalized = normalize_string(league_name)
        
        return f"{country_normalized}_{league_normalized}"
    
    @staticmethod
    def generate_season_id(liga_id: str, season_year: int) -> str:
        """Genera un ID de temporada estructurado.
        
        Args:
            liga_id: ID de la liga transformado
            season_year: Año de inicio de la temporada
            
        Returns:
            ID de temporada (ej: SPAIN_LA_LIGA_2023-24)
        """
        # Las temporadas futbolísticas van de agosto a mayo
        # Formato: LIGA_YYYY-YY
        next_year = (season_year + 1) % 100  # Solo últimos 2 dígitos
        return f"{liga_id}_{season_year}-{next_year:02d}"
    
    @staticmethod
    def generate_match_id(
        liga_id: str,
        season_year: int,
        ronda: str,
        equipo_local: str,
        equipo_visitante: str,
        fecha: str
    ) -> str:
        """Genera un ID único para el partido.
        
        Args:
            liga_id: ID de la liga
            season_year: Año de la temporada
            ronda: Ronda/jornada del partido
            equipo_local: Nombre del equipo local
            equipo_visitante: Nombre del equipo visitante
            fecha: Fecha del partido
            
        Returns:
            ID único del partido
        """
        # Normalizar nombres de equipos (primeras 3 letras)
        local_code = normalize_string(equipo_local)[:3].upper()
        visit_code = normalize_string(equipo_visitante)[:3].upper()
        
        # Extraer número de jornada si existe
        jornada = ""
        if ronda:
            # Intentar extraer número de la ronda
            import re
            match = re.search(r'(\d+)', ronda)
            if match:
                jornada = f"J{match.group(1)}"
            else:
                jornada = normalize_string(ronda)[:10]
        
        # Formato: LIGA_SEASON_JORNADA_LOCAL-VISIT_FECHA
        season_id = DataTransformer.generate_season_id(liga_id, season_year)
        fecha_short = fecha.replace("-", "") if fecha else ""
        
        return f"{season_id}_{jornada}_{local_code}-{visit_code}_{fecha_short}"
    
    @staticmethod
    def infer_season_from_date(fecha: str, season_hint: int = None) -> int:
        """Infiere el año de inicio de temporada basándose en la fecha.
        
        Las temporadas europeas generalmente van de agosto a mayo.
        
        Args:
            fecha: Fecha del partido (YYYY-MM-DD)
            season_hint: Año sugerido por la API
            
        Returns:
            Año de inicio de la temporada
        """
        if not fecha:
            return season_hint or 2023
        
        try:
            fecha_dt = datetime.strptime(fecha, "%Y-%m-%d")
            
            # Si el mes es >= 8 (agosto), es el inicio de temporada
            # Si el mes es < 8, pertenece a la temporada del año anterior
            if fecha_dt.month >= 8:
                return fecha_dt.year
            else:
                return fecha_dt.year - 1
        except:
            return season_hint or 2023
    
    @staticmethod
    def extract_match_data(
        fixture: Dict,
        league_info: Dict,
        standings: Optional[Dict[int, int]] = None
    ) -> Optional[Dict[str, Any]]:
        """Extrae y transforma los datos de un partido.
        
        Args:
            fixture: Datos del partido desde la API
            league_info: Información de la liga
            standings: Diccionario con posiciones de equipos {team_id: posición}
            
        Returns:
            Diccionario con datos transformados o None si falta información crítica
        """
        try:
            # Extraer datos básicos del fixture
            fixture_data = fixture.get('fixture', {})
            teams = fixture.get('teams', {})
            goals = fixture.get('goals', {})
            score = fixture.get('score', {})
            league = fixture.get('league', {})
            
            # Validar que existan los datos mínimos necesarios
            if not fixture_data or not teams:
                logger.warning("Fixture sin datos mínimos necesarios")
                return None
            
            # Extraer equipos
            home_team = teams.get('home', {})
            away_team = teams.get('away', {})
            
            if not home_team or not away_team:
                logger.warning(f"Fixture {fixture_data.get('id')} sin equipos completos")
                return None
            
            # Extraer IDs de equipos
            home_team_id = home_team.get('id')
            away_team_id = away_team.get('id')
            
            # Obtener posiciones de clasificación
            home_position = standings.get(home_team_id, 0) if standings else 0
            away_position = standings.get(away_team_id, 0) if standings else 0
            
            # Extraer fecha y hora
            fixture_date = fixture_data.get('date', '')
            fecha = ''
            hora = ''
            
            if fixture_date:
                try:
                    dt = datetime.fromisoformat(fixture_date.replace('Z', '+00:00'))
                    fecha = dt.strftime('%Y-%m-%d')
                    hora = dt.strftime('%H:%M')
                except Exception as e:
                    logger.warning(f"Error parseando fecha {fixture_date}: {str(e)}")
            
            # Extraer goles
            halftime_score = score.get('halftime', {})
            fulltime_score = score.get('fulltime', {})
            
            goles_local_1mt = halftime_score.get('home') if halftime_score.get('home') is not None else 0
            goles_local_tr = fulltime_score.get('home') if fulltime_score.get('home') is not None else 0
            goles_visitante_1mt = halftime_score.get('away') if halftime_score.get('away') is not None else 0
            goles_visitante_tr = fulltime_score.get('away') if fulltime_score.get('away') is not None else 0
            
            # Transformar liga_id
            country = league_info.get('country', {}).get('name', 'UNKNOWN')
            league_name = league_info.get('league', {}).get('name', 'UNKNOWN')
            liga_id_transformed = DataTransformer.transform_league_id(country, league_name)
            
            # Obtener datos de temporada
            api_season = league.get('season', 2023)
            ronda = league.get('round', '')
            equipo_local_nombre = home_team.get('name', '')
            equipo_visitante_nombre = away_team.get('name', '')
            
            # Inferir temporada correcta basándose en fecha
            season_year = DataTransformer.infer_season_from_date(fecha, api_season)
            
            # Generar IDs estructurados
            season_id = DataTransformer.generate_season_id(liga_id_transformed, season_year)
            match_id = DataTransformer.generate_match_id(
                liga_id_transformed,
                season_year,
                ronda,
                equipo_local_nombre,
                equipo_visitante_nombre,
                fecha
            )
            
            # Construir el documento final
            match_data = {
                # === NUEVOS CAMPOS DE IDENTIFICACIÓN ===
                'match_id': match_id,                    # ID interno único
                'season_id': season_id,                  # ID de temporada estructurado
                'external_match_id': fixture_data.get('id'),  # ID de la API externa
                
                # === CAMPOS LEGACY (mantener para compatibilidad) ===
                'id_partido': fixture_data.get('id'),    # DEPRECADO - usar external_match_id
                'season': api_season,                    # DEPRECADO - usar season_id
                
                # === DATOS DEL PARTIDO ===
                'equipo_local': equipo_local_nombre,
                'equipo_visitante': equipo_visitante_nombre,
                'estado_del_partido': fixture_data.get('status', {}).get('long', ''),
                'fecha': fecha,
                'hora': hora,
                'ronda': ronda,
                
                # === GOLES ===
                'goles_local_1MT': goles_local_1mt,
                'goles_local_TR': goles_local_tr,
                'goles_visitante_1MT': goles_visitante_1mt,
                'goles_visitante_TR': goles_visitante_tr,
                
                # === IDS DE EQUIPOS ===
                'id_equipo_local': home_team_id,
                'id_equipo_visitante': away_team_id,
                
                # === LIGA ===
                'liga_id': liga_id_transformed,
                'liga_nombre': league_name,
                'api_league_id': league_info.get('league', {}).get('id'),
                
                # === CLASIFICACIÓN ===
                'pos_clasif_local': home_position,
                'pos_clasif_visita': away_position,
                
                # === METADATA ===
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            return match_data
            
        except Exception as e:
            logger.error(f"Error transformando fixture: {str(e)}")
            return None
    
    @staticmethod
    def batch_transform(
        fixtures: List[Dict],
        league_info: Dict,
        standings: Optional[Dict[int, int]] = None
    ) -> List[Dict[str, Any]]:
        """Transforma un lote de fixtures.
        
        Args:
            fixtures: Lista de fixtures desde la API
            league_info: Información de la liga
            standings: Diccionario con posiciones de equipos
            
        Returns:
            Lista de datos transformados
        """
        transformed_data = []
        
        for fixture in fixtures:
            match_data = DataTransformer.extract_match_data(
                fixture,
                league_info,
                standings
            )
            
            if match_data:
                transformed_data.append(match_data)
        
        logger.info(f"Transformados {len(transformed_data)} de {len(fixtures)} fixtures")
        
        return transformed_data
