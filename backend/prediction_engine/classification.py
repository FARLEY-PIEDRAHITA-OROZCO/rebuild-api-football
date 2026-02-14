"""
========================================
MÓDULO: classification.py
========================================

Motor de Clasificación - Equivalente a hojas clasificacion del Excel.

Este módulo genera tablas de clasificación (posiciones) basadas
en las estadísticas de los equipos.

Criterios de Ordenamiento:
-------------------------
1. Puntos (mayor a menor)
2. Diferencia de goles (mayor a menor)
3. Goles a favor (mayor a menor)
4. Nombre del equipo (alfabético, desempate final)

Clases:
-------
- ClassificationEngine: Motor de clasificación

Historial de Cambios:
--------------------
- v1.0.0 (Dic 2024): Versión inicial
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import logging

from .models import (
    Equipo,
    FilaClasificacion,
    TablaClasificacion,
    EstadisticasEquipo
)
from .config import Config, TipoTiempo
from .stats_builder import StatsBuilder

logger = logging.getLogger(__name__)


class ClassificationEngine:
    """
    Motor de clasificación de equipos.
    
    Genera tablas de posiciones ordenadas por puntos,
    diferencia de goles y goles a favor.
    
    Atributos:
    ----------
    db : AsyncIOMotorDatabase
        Conexión a MongoDB
    stats_builder : StatsBuilder
        Constructor de estadísticas
    
    Métodos Públicos:
    ----------------
    generar_clasificacion(liga_id, temporada, tipo_tiempo)
        Genera tabla de clasificación completa
    
    obtener_posicion(equipo, liga_id, tipo_tiempo)
        Obtiene la posición de un equipo específico
    
    Ejemplo de Uso:
    ---------------
    ```python
    engine = ClassificationEngine(db)
    tabla = await engine.generar_clasificacion(
        'SPAIN_LA_LIGA',
        2023,
        TipoTiempo.COMPLETO
    )
    
    for fila in tabla.filas:
        print(f"{fila.posicion}. {fila.equipo}: {fila.pts} pts")
    ```
    """
    
    def __init__(self, db):
        """
        Inicializa el motor de clasificación.
        
        Parámetros:
        -----------
        db : AsyncIOMotorDatabase
            Conexión a MongoDB
        """
        self.db = db
        self.stats_builder = StatsBuilder(db)
        logger.info("ClassificationEngine inicializado")
    
    async def generar_clasificacion(
        self,
        liga_id: str,
        temporada: Optional[int] = None,
        tipo_tiempo: TipoTiempo = TipoTiempo.COMPLETO,
        season_id: Optional[str] = None
    ) -> TablaClasificacion:
        """
        Genera la tabla de clasificación para una liga.
        
        Parámetros:
        -----------
        liga_id : str
            ID de la liga
        temporada : int, optional
            Año de la temporada (legacy)
        tipo_tiempo : TipoTiempo
            COMPLETO, PRIMER_TIEMPO o SEGUNDO_TIEMPO
        season_id : str, optional
            ID de temporada estructurado (preferido)
        
        Retorna:
        --------
        TablaClasificacion
            Tabla con equipos ordenados por posición
        
        Raises:
        -------
        ValueError
            Si no hay equipos en la liga
        
        Lógica de Ordenamiento:
        ----------------------
        1. Puntos (DESC) - Más puntos = mejor posición
        2. Diferencia de goles (DESC) - Mayor diferencia = mejor
        3. Goles a favor (DESC) - Más goles = mejor
        4. Nombre (ASC) - Desempate alfabético
        
        Ejemplo:
        --------
        ```python
        # Clasificación con season_id (preferido)
        tabla = await engine.generar_clasificacion(
            'SPAIN_LA_LIGA',
            season_id='SPAIN_LA_LIGA_2023-24',
            tipo_tiempo=TipoTiempo.COMPLETO
        )
        
        # Clasificación legacy
        tabla = await engine.generar_clasificacion(
            'SPAIN_LA_LIGA', 2023, TipoTiempo.COMPLETO
        )
        ```
        """
        logger.info(f"Generando clasificación para {liga_id}, season_id={season_id}, tiempo: {tipo_tiempo.value}")
        
        # Obtener todos los equipos
        equipos = await self.stats_builder.obtener_todos_equipos(
            liga_id, 
            temporada,
            season_id=season_id
        )
        
        if not equipos:
            logger.warning(f"No hay equipos para {liga_id}")
            raise ValueError(f"No hay equipos para generar clasificación en {liga_id}")
        
        # Crear filas de clasificación
        filas: List[FilaClasificacion] = []
        
        for equipo in equipos:
            stats = equipo.obtener_stats(tipo_tiempo)
            
            fila = FilaClasificacion(
                posicion=0,  # Se asignará después de ordenar
                equipo=equipo.nombre,
                
                # Generales
                pj=stats.partidos_jugados,
                v=stats.victorias,
                e=stats.empates,
                d=stats.derrotas,
                gf=stats.goles_favor,
                gc=stats.goles_contra,
                dif=stats.diferencia_goles,
                pts=stats.puntos,
                
                # Local
                pj_l=stats.pj_local,
                v_l=stats.v_local,
                e_l=stats.e_local,
                d_l=stats.d_local,
                gf_l=stats.gf_local,
                gc_l=stats.gc_local,
                pts_l=stats.pts_local,
                
                # Visitante
                pj_v=stats.pj_visita,
                v_v=stats.v_visita,
                e_v=stats.e_visita,
                d_v=stats.d_visita,
                gf_v=stats.gf_visita,
                gc_v=stats.gc_visita,
                pts_v=stats.pts_visita,
                
                # Rendimientos
                rendimiento=stats.rendimiento_general,
                rendimiento_l=stats.rendimiento_local,
                rendimiento_v=stats.rendimiento_visita
            )
            filas.append(fila)
        
        # Ordenar por criterios
        # 1. Puntos (mayor a menor)
        # 2. Diferencia de goles (mayor a menor)
        # 3. Goles a favor (mayor a menor)
        # 4. Nombre (A-Z para desempate)
        filas.sort(
            key=lambda x: (-x.pts, -x.dif, -x.gf, x.equipo)
        )
        
        # Asignar posiciones
        for idx, fila in enumerate(filas, 1):
            fila.posicion = idx
        
        # Crear tabla
        tabla = TablaClasificacion(
            liga_id=liga_id,
            temporada=temporada or 2023,
            tipo_tiempo=tipo_tiempo.value,
            filas=filas,
            fecha_actualizacion=datetime.now(timezone.utc)
        )
        
        logger.info(f"Clasificación generada con {len(filas)} equipos")
        return tabla
    
    async def obtener_posicion(
        self,
        nombre_equipo: str,
        liga_id: str,
        temporada: Optional[int] = None,
        tipo_tiempo: TipoTiempo = TipoTiempo.COMPLETO
    ) -> Optional[int]:
        """
        Obtiene la posición de un equipo específico.
        
        Parámetros:
        -----------
        nombre_equipo : str
            Nombre del equipo
        liga_id : str
            ID de la liga
        temporada : int, optional
            Año de la temporada
        tipo_tiempo : TipoTiempo
            Tipo de tiempo para la clasificación
        
        Retorna:
        --------
        int or None
            Posición del equipo (1 = primero), None si no existe
        
        Ejemplo:
        --------
        ```python
        pos = await engine.obtener_posicion('Barcelona', 'SPAIN_LA_LIGA')
        print(f"Barcelona está en posición {pos}")
        ```
        """
        tabla = await self.generar_clasificacion(liga_id, temporada, tipo_tiempo)
        
        for fila in tabla.filas:
            if fila.equipo.lower() == nombre_equipo.lower():
                return fila.posicion
        
        return None
    
    async def obtener_stats_posicion(
        self,
        nombre_equipo: str,
        liga_id: str,
        temporada: Optional[int] = None,
        tipo_tiempo: TipoTiempo = TipoTiempo.COMPLETO
    ) -> Optional[FilaClasificacion]:
        """
        Obtiene la fila de clasificación completa de un equipo.
        
        Parámetros:
        -----------
        nombre_equipo : str
            Nombre del equipo
        liga_id : str
            ID de la liga
        temporada : int, optional
            Año
        tipo_tiempo : TipoTiempo
            Tipo de tiempo
        
        Retorna:
        --------
        FilaClasificacion or None
            Todos los datos de clasificación del equipo
        """
        tabla = await self.generar_clasificacion(liga_id, temporada, tipo_tiempo)
        
        for fila in tabla.filas:
            if fila.equipo.lower() == nombre_equipo.lower():
                return fila
        
        return None
    
    def tabla_to_dict(self, tabla: TablaClasificacion) -> Dict[str, Any]:
        """
        Convierte una tabla de clasificación a diccionario.
        
        Útil para respuestas API.
        
        Parámetros:
        -----------
        tabla : TablaClasificacion
            Tabla a convertir
        
        Retorna:
        --------
        Dict
            Diccionario con la tabla
        """
        return {
            'liga_id': tabla.liga_id,
            'temporada': tabla.temporada,
            'tipo_tiempo': tabla.tipo_tiempo,
            'total_equipos': len(tabla.filas),
            'fecha_actualizacion': tabla.fecha_actualizacion.isoformat(),
            'clasificacion': [
                {
                    'posicion': f.posicion,
                    'equipo': f.equipo,
                    'pj': f.pj,
                    'v': f.v,
                    'e': f.e,
                    'd': f.d,
                    'gf': f.gf,
                    'gc': f.gc,
                    'dif': f.dif,
                    'pts': f.pts,
                    'rendimiento': f.rendimiento,
                    'local': {
                        'pj': f.pj_l,
                        'v': f.v_l,
                        'e': f.e_l,
                        'd': f.d_l,
                        'gf': f.gf_l,
                        'gc': f.gc_l,
                        'pts': f.pts_l,
                        'rendimiento': f.rendimiento_l
                    },
                    'visitante': {
                        'pj': f.pj_v,
                        'v': f.v_v,
                        'e': f.e_v,
                        'd': f.d_v,
                        'gf': f.gf_v,
                        'gc': f.gc_v,
                        'pts': f.pts_v,
                        'rendimiento': f.rendimiento_v
                    }
                }
                for f in tabla.filas
            ]
        }
