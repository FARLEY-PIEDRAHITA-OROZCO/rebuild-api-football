"""Cliente para consumir la API de API-Futbol."""
import requests
import time
from typing import Dict, List, Optional, Any
from .config import (
    API_FOOTBALL_KEY,
    API_FOOTBALL_BASE_URL,
    API_TIMEOUT,
    MAX_RETRIES,
    RETRY_DELAY
)
from .utils import setup_logger

logger = setup_logger(__name__)


class APIFootballClient:
    """Cliente para interactuar con la API de API-Futbol."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Inicializa el cliente de la API.
        
        Args:
            api_key: API key de API-Futbol. Si no se proporciona, usa la del config.
        """
        self.api_key = api_key or API_FOOTBALL_KEY
        self.base_url = API_FOOTBALL_BASE_URL
        self.headers = {
            'x-rapidapi-key': self.api_key,
            'x-rapidapi-host': 'api-football-v1.p.rapidapi.com'
        }
        
        if not self.api_key:
            raise ValueError("API key no configurada. Verifica el archivo .env")
        
        logger.info("Cliente API-Futbol inicializado correctamente")
    
    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict]:
        """Realiza una petición HTTP a la API con reintentos.
        
        Args:
            endpoint: Endpoint de la API
            params: Parámetros de la petición
            
        Returns:
            Respuesta JSON de la API o None si falla
        """
        url = f"{self.base_url}/{endpoint}"
        
        for attempt in range(MAX_RETRIES):
            try:
                logger.debug(f"Petición a {endpoint} (intento {attempt + 1}/{MAX_RETRIES})")
                
                response = requests.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=API_TIMEOUT
                )
                
                # Verificar códigos de respuesta
                if response.status_code == 200:
                    data = response.json()
                    
                    # Verificar si hay errores en la respuesta
                    if data.get('errors'):
                        logger.error(f"Error en la API: {data['errors']}")
                        return None
                    
                    logger.debug(f"Petición exitosa a {endpoint}")
                    return data
                    
                elif response.status_code == 429:
                    logger.warning("Rate limit alcanzado. Esperando...")
                    time.sleep(RETRY_DELAY * 2)
                    continue
                    
                elif response.status_code >= 500:
                    logger.error(f"Error del servidor: {response.status_code}")
                    time.sleep(RETRY_DELAY)
                    continue
                    
                else:
                    logger.error(f"Error HTTP {response.status_code}: {response.text}")
                    return None
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout en {endpoint}. Reintentando...")
                time.sleep(RETRY_DELAY)
                
            except requests.exceptions.ConnectionError:
                logger.error(f"Error de conexión en {endpoint}")
                time.sleep(RETRY_DELAY)
                
            except Exception as e:
                logger.error(f"Error inesperado: {str(e)}")
                return None
        
        logger.error(f"Todos los intentos fallaron para {endpoint}")
        return None
    
    def get_all_leagues(self) -> List[Dict]:
        """Obtiene todas las ligas disponibles.
        
        Returns:
            Lista de ligas
        """
        logger.info("Obteniendo todas las ligas...")
        
        response = self._make_request('leagues')
        
        if not response or 'response' not in response:
            logger.error("No se pudieron obtener las ligas")
            return []
        
        leagues = response['response']
        logger.info(f"Se encontraron {len(leagues)} ligas")
        
        return leagues
    
    def get_fixtures_by_league(
        self,
        league_id: int,
        season: int = 2023
    ) -> List[Dict]:
        """Obtiene los partidos (fixtures) de una liga específica.
        
        Args:
            league_id: ID de la liga
            season: Temporada (año). Free plan: 2021-2023
            
        Returns:
            Lista de partidos
        """
        logger.info(f"Obteniendo partidos de la liga {league_id}, temporada {season}...")
        
        params = {
            'league': league_id,
            'season': season
        }
        
        response = self._make_request('fixtures', params)
        
        if not response or 'response' not in response:
            logger.warning(f"No se pudieron obtener partidos de la liga {league_id}")
            return []
        
        fixtures = response['response']
        logger.info(f"Se encontraron {len(fixtures)} partidos para la liga {league_id}")
        
        return fixtures
    
    def get_team_standings(
        self,
        league_id: int,
        season: int = 2023
    ) -> Dict[int, int]:
        """Obtiene la posición de clasificación de los equipos en una liga.
        
        Args:
            league_id: ID de la liga
            season: Temporada (año). Free plan: 2021-2023
            
        Returns:
            Diccionario {team_id: posición}
        """
        logger.info(f"Obteniendo clasificación de la liga {league_id}...")
        
        params = {
            'league': league_id,
            'season': season
        }
        
        response = self._make_request('standings', params)
        
        if not response or 'response' not in response:
            logger.warning(f"No se pudo obtener clasificación de la liga {league_id}")
            return {}
        
        standings_map = {}
        
        try:
            # La API puede retornar múltiples grupos/divisiones
            for league_data in response['response']:
                if 'league' in league_data and 'standings' in league_data['league']:
                    for group in league_data['league']['standings']:
                        for team_standing in group:
                            team_id = team_standing['team']['id']
                            rank = team_standing['rank']
                            standings_map[team_id] = rank
            
            logger.info(f"Se obtuvieron posiciones de {len(standings_map)} equipos")
            
        except Exception as e:
            logger.error(f"Error procesando clasificación: {str(e)}")
        
        return standings_map
