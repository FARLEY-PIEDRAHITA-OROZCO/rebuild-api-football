"""Gestor de base de datos MongoDB."""
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError, PyMongoError
from typing import List, Dict, Any, Optional
from datetime import datetime
from .config import MONGO_URL, DB_NAME, COLLECTION_NAME, SEASONS_COLLECTION
from .utils import setup_logger

logger = setup_logger(__name__)


class DatabaseManager:
    """Gestor para operaciones con MongoDB."""
    
    def __init__(
        self,
        mongo_url: Optional[str] = None,
        db_name: Optional[str] = None,
        collection_name: Optional[str] = None
    ):
        """Inicializa el gestor de base de datos.
        
        Args:
            mongo_url: URL de conexión a MongoDB
            db_name: Nombre de la base de datos
            collection_name: Nombre de la colección
        """
        self.mongo_url = mongo_url or MONGO_URL
        self.db_name = db_name or DB_NAME
        self.collection_name = collection_name or COLLECTION_NAME
        
        self.client: Optional[MongoClient] = None
        self.db = None
        self.collection = None
        self.seasons_collection = None
        
        logger.info(f"DatabaseManager inicializado para BD: {self.db_name}")
    
    def connect(self) -> bool:
        """Establece conexión con MongoDB.
        
        Returns:
            True si la conexión fue exitosa, False en caso contrario
        """
        try:
            self.client = MongoClient(self.mongo_url, serverSelectionTimeoutMS=5000)
            
            # Verificar conexión
            self.client.server_info()
            
            self.db = self.client[self.db_name]
            self.collection = self.db[self.collection_name]
            self.seasons_collection = self.db[SEASONS_COLLECTION]
            
            logger.info(f"Conexión exitosa a MongoDB: {self.db_name}.{self.collection_name}")
            
            # Crear índices
            self._create_indexes()
            
            return True
            
        except PyMongoError as e:
            logger.error(f"Error conectando a MongoDB: {str(e)}")
            return False
    
    def _create_indexes(self):
        """Crea índices necesarios en las colecciones."""
        try:
            # ============================================
            # ÍNDICES PARA football_matches
            # ============================================
            
            # Índice único para match_id (nuevo identificador principal)
            self.collection.create_index(
                [('match_id', ASCENDING)],
                unique=True,
                sparse=True,  # Permitir documentos sin match_id (legacy)
                name='idx_match_id'
            )
            
            # Índice único para id_partido (legacy, mantener para compatibilidad)
            self.collection.create_index(
                [('id_partido', ASCENDING)],
                unique=True,
                name='idx_id_partido'
            )
            
            # Índice para season_id (nuevo)
            self.collection.create_index(
                [('season_id', ASCENDING)],
                sparse=True,
                name='idx_season_id'
            )
            
            # Índice compuesto para consultas por liga, temporada y fecha
            self.collection.create_index(
                [('season_id', ASCENDING), ('liga_id', ASCENDING), ('fecha', ASCENDING)],
                name='idx_season_liga_fecha'
            )
            
            # Índice compuesto legacy para consultas por liga y fecha
            self.collection.create_index(
                [('liga_id', ASCENDING), ('fecha', ASCENDING)],
                name='idx_liga_fecha'
            )
            
            # Índice para búsquedas por equipos
            self.collection.create_index(
                [('id_equipo_local', ASCENDING)],
                name='idx_equipo_local'
            )
            
            self.collection.create_index(
                [('id_equipo_visitante', ASCENDING)],
                name='idx_equipo_visitante'
            )
            
            # ============================================
            # ÍNDICES PARA seasons
            # ============================================
            
            self.seasons_collection.create_index(
                [('season_id', ASCENDING)],
                unique=True,
                name='idx_seasons_season_id'
            )
            
            self.seasons_collection.create_index(
                [('liga_id', ASCENDING), ('year', DESCENDING)],
                name='idx_seasons_liga_year'
            )
            
            logger.info("Índices creados correctamente")
            
        except PyMongoError as e:
            logger.warning(f"Error creando índices: {str(e)}")
    
    def insert_match(self, match_data: Dict[str, Any]) -> bool:
        """Inserta un partido en la base de datos.
        
        Args:
            match_data: Datos del partido
            
        Returns:
            True si se insertó correctamente, False si ya existe o hubo error
        """
        try:
            self.collection.insert_one(match_data)
            return True
            
        except DuplicateKeyError:
            # Intentar actualizar si ya existe
            match_id = match_data.get('match_id') or match_data.get('id_partido')
            logger.debug(f"Partido {match_id} ya existe, actualizando...")
            return self._update_existing_match(match_data)
            
        except PyMongoError as e:
            logger.error(f"Error insertando partido: {str(e)}")
            return False
    
    def _update_existing_match(self, match_data: Dict[str, Any]) -> bool:
        """Actualiza un partido existente con nuevos campos.
        
        Args:
            match_data: Datos del partido
            
        Returns:
            True si se actualizó correctamente
        """
        try:
            # Buscar por match_id o id_partido
            query = {}
            if match_data.get('match_id'):
                query['match_id'] = match_data['match_id']
            elif match_data.get('id_partido'):
                query['id_partido'] = match_data['id_partido']
            else:
                return False
            
            # Actualizar campos, incluyendo nuevos season_id y match_id
            match_data['updated_at'] = datetime.utcnow().isoformat()
            
            result = self.collection.update_one(
                query,
                {'$set': match_data}
            )
            
            return result.modified_count > 0 or result.matched_count > 0
            
        except PyMongoError as e:
            logger.error(f"Error actualizando partido: {str(e)}")
            return False
    
    def insert_many_matches(self, matches_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """Inserta múltiples partidos en la base de datos.
        
        Args:
            matches_data: Lista de datos de partidos
            
        Returns:
            Diccionario con estadísticas de inserción
        """
        stats = {
            'insertados': 0,
            'actualizados': 0,
            'duplicados': 0,
            'errores': 0
        }
        
        for match_data in matches_data:
            try:
                self.collection.insert_one(match_data)
                stats['insertados'] += 1
                
            except DuplicateKeyError:
                # Actualizar partido existente con nuevos campos
                if self._update_existing_match(match_data):
                    stats['actualizados'] += 1
                else:
                    stats['duplicados'] += 1
                
            except PyMongoError as e:
                logger.error(f"Error insertando partido: {str(e)}")
                stats['errores'] += 1
        
        logger.info(
            f"Inserción completada - "
            f"Insertados: {stats['insertados']}, "
            f"Actualizados: {stats['actualizados']}, "
            f"Duplicados: {stats['duplicados']}, "
            f"Errores: {stats['errores']}"
        )
        
        return stats
    
    def upsert_season(self, season_data: Dict[str, Any]) -> bool:
        """Inserta o actualiza una temporada.
        
        Args:
            season_data: Datos de la temporada
            
        Returns:
            True si se guardó correctamente
        """
        try:
            result = self.seasons_collection.update_one(
                {'season_id': season_data['season_id']},
                {'$set': season_data},
                upsert=True
            )
            return True
        except PyMongoError as e:
            logger.error(f"Error guardando temporada: {str(e)}")
            return False
    
    def get_seasons_by_league(self, liga_id: str) -> List[Dict[str, Any]]:
        """Obtiene las temporadas de una liga.
        
        Args:
            liga_id: ID de la liga
            
        Returns:
            Lista de temporadas ordenadas por año descendente
        """
        try:
            return list(self.seasons_collection.find(
                {'liga_id': liga_id},
                {'_id': 0}
            ).sort('year', DESCENDING))
        except PyMongoError as e:
            logger.error(f"Error obteniendo temporadas: {str(e)}")
            return []
    
    def update_match(self, match_id: int, update_data: Dict[str, Any]) -> bool:
        """Actualiza un partido existente.
        
        Args:
            match_id: ID del partido
            update_data: Datos a actualizar
            
        Returns:
            True si se actualizó correctamente
        """
        try:
            result = self.collection.update_one(
                {'id_partido': match_id},
                {'$set': update_data}
            )
            
            if result.modified_count > 0:
                logger.info(f"Partido {match_id} actualizado")
                return True
            else:
                logger.debug(f"Partido {match_id} no encontrado para actualizar")
                return False
                
        except PyMongoError as e:
            logger.error(f"Error actualizando partido: {str(e)}")
            return False
    
    def get_match_by_id(self, match_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene un partido por su ID.
        
        Args:
            match_id: ID del partido
            
        Returns:
            Datos del partido o None si no existe
        """
        try:
            return self.collection.find_one({'id_partido': match_id}, {'_id': 0})
        except PyMongoError as e:
            logger.error(f"Error obteniendo partido: {str(e)}")
            return None
    
    def get_matches_by_season(self, season_id: str, limit: int = 0) -> List[Dict[str, Any]]:
        """Obtiene partidos de una temporada específica.
        
        Args:
            season_id: ID de la temporada
            limit: Límite de resultados (0 = sin límite)
            
        Returns:
            Lista de partidos
        """
        try:
            cursor = self.collection.find(
                {'season_id': season_id},
                {'_id': 0}
            ).sort('fecha', ASCENDING)
            
            if limit > 0:
                cursor = cursor.limit(limit)
            
            return list(cursor)
            
        except PyMongoError as e:
            logger.error(f"Error obteniendo partidos: {str(e)}")
            return []
    
    def get_matches_by_league(self, liga_id: str, limit: int = 0) -> List[Dict[str, Any]]:
        """Obtiene partidos de una liga específica.
        
        Args:
            liga_id: ID de la liga transformado
            limit: Límite de resultados (0 = sin límite)
            
        Returns:
            Lista de partidos
        """
        try:
            cursor = self.collection.find(
                {'liga_id': liga_id},
                {'_id': 0}
            ).sort('fecha', ASCENDING)
            
            if limit > 0:
                cursor = cursor.limit(limit)
            
            return list(cursor)
            
        except PyMongoError as e:
            logger.error(f"Error obteniendo partidos: {str(e)}")
            return []
    
    def count_matches(self) -> int:
        """Cuenta el total de partidos en la colección.
        
        Returns:
            Número total de partidos
        """
        try:
            return self.collection.count_documents({})
        except PyMongoError as e:
            logger.error(f"Error contando partidos: {str(e)}")
            return 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas de la colección.
        
        Returns:
            Diccionario con estadísticas
        """
        try:
            total_matches = self.count_matches()
            
            # Contar partidos por liga
            leagues_pipeline = [
                {'$group': {
                    '_id': '$liga_id',
                    'count': {'$sum': 1},
                    'liga_nombre': {'$first': '$liga_nombre'}
                }},
                {'$sort': {'count': -1}}
            ]
            
            leagues_stats = list(self.collection.aggregate(leagues_pipeline))
            
            # Contar partidos por temporada
            seasons_pipeline = [
                {'$group': {
                    '_id': '$season_id',
                    'count': {'$sum': 1}
                }},
                {'$sort': {'_id': -1}}
            ]
            
            seasons_stats = list(self.collection.aggregate(seasons_pipeline))
            
            return {
                'total_partidos': total_matches,
                'total_ligas': len(leagues_stats),
                'partidos_por_liga': leagues_stats[:10],  # Top 10
                'partidos_por_temporada': seasons_stats[:10]  # Top 10
            }
            
        except PyMongoError as e:
            logger.error(f"Error obteniendo estadísticas: {str(e)}")
            return {}
    
    def close(self):
        """Cierra la conexión con MongoDB."""
        if self.client:
            self.client.close()
            logger.info("Conexión a MongoDB cerrada")
