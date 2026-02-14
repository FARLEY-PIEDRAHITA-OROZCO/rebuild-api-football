"""
========================================
MÓDULO: historico_consolidado.py
========================================

Motor de Histórico Consolidado - Fase 2

Este módulo permite que el motor de pronósticos use datos de múltiples
temporadas para mejorar las predicciones, implementando:

1. Estadísticas ponderadas (temporada actual 70% + históricas 30%)
2. Historial de enfrentamientos directos (H2H)
3. Tendencias a largo plazo por equipo

Historial de Cambios:
--------------------
- v1.0.0 (Dic 2024): Versión inicial
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class HistoricoConsolidado:
    """
    Motor de Histórico Consolidado.
    
    Combina datos de múltiples temporadas para mejorar predicciones.
    """
    
    # Pesos para ponderación
    PESO_TEMPORADA_ACTUAL = 0.70
    PESO_HISTORICO = 0.30
    
    def __init__(self, db):
        """
        Inicializa el motor de histórico.
        
        Parámetros:
        -----------
        db : AsyncIOMotorDatabase
            Conexión a MongoDB
        """
        self.db = db
        logger.info("HistoricoConsolidado inicializado")
    
    async def obtener_temporadas_disponibles(
        self, 
        liga_id: str,
        equipo: Optional[str] = None
    ) -> List[str]:
        """
        Obtiene todas las temporadas disponibles para una liga/equipo.
        
        Retorna lista de season_ids ordenados de más reciente a más antiguo.
        """
        query = {"liga_id": liga_id}
        if equipo:
            query["$or"] = [
                {"equipo_local": equipo},
                {"equipo_visitante": equipo}
            ]
        
        pipeline = [
            {"$match": query},
            {"$group": {"_id": "$season_id"}},
            {"$sort": {"_id": -1}}
        ]
        
        result = await self.db.football_matches.aggregate(pipeline).to_list(20)
        return [r["_id"] for r in result if r["_id"]]
    
    async def obtener_stats_historicas(
        self,
        equipo: str,
        liga_id: str,
        temporadas: int = 3
    ) -> Dict[str, Any]:
        """
        Obtiene estadísticas históricas consolidadas de un equipo.
        
        Parámetros:
        -----------
        equipo : str
            Nombre del equipo
        liga_id : str
            ID de la liga
        temporadas : int
            Número de temporadas a considerar (default: 3)
        
        Retorna:
        --------
        Dict con estadísticas ponderadas
        """
        # Obtener temporadas disponibles
        seasons = await self.obtener_temporadas_disponibles(liga_id, equipo)
        
        if not seasons:
            return None
        
        # Limitar a las últimas N temporadas
        seasons = seasons[:temporadas]
        
        # Obtener stats de cada temporada desde team_statistics
        stats_por_temporada = []
        
        for season_id in seasons:
            stats = await self.db.team_statistics.find_one(
                {"nombre": equipo, "season_id": season_id},
                {"_id": 0}
            )
            if stats and "stats_completo" in stats:
                stats_por_temporada.append({
                    "season_id": season_id,
                    "stats": stats["stats_completo"]
                })
        
        if not stats_por_temporada:
            return None
        
        # Calcular estadísticas ponderadas
        return self._calcular_stats_ponderadas(stats_por_temporada)
    
    def _calcular_stats_ponderadas(
        self, 
        stats_por_temporada: List[Dict]
    ) -> Dict[str, Any]:
        """
        Calcula estadísticas ponderadas de múltiples temporadas.
        
        La temporada más reciente tiene mayor peso.
        """
        if len(stats_por_temporada) == 1:
            return {
                "stats": stats_por_temporada[0]["stats"],
                "temporadas_usadas": 1,
                "peso_actual": 1.0
            }
        
        # Pesos decrecientes: [0.7, 0.2, 0.1] para 3 temporadas
        pesos = self._calcular_pesos(len(stats_por_temporada))
        
        # Campos a ponderar
        campos_numericos = [
            "rendimiento_general", "rendimiento_local", "rendimiento_visita",
            "promedio_gf", "promedio_gc", "puntos"
        ]
        
        campos_acumulativos = [
            "victorias", "empates", "derrotas", "goles_favor", "goles_contra",
            "partidos_jugados"
        ]
        
        stats_ponderadas = {}
        total_partidos = 0
        
        # Calcular promedios ponderados
        for campo in campos_numericos:
            valor_ponderado = 0
            for i, item in enumerate(stats_por_temporada):
                valor = item["stats"].get(campo, 0)
                if valor:
                    valor_ponderado += valor * pesos[i]
            stats_ponderadas[campo] = round(valor_ponderado, 2)
        
        # Sumar campos acumulativos (para referencia)
        for campo in campos_acumulativos:
            total = sum(item["stats"].get(campo, 0) for item in stats_por_temporada)
            stats_ponderadas[f"{campo}_total"] = total
        
        total_partidos = sum(
            item["stats"].get("partidos_jugados", 0) 
            for item in stats_por_temporada
        )
        
        return {
            "stats": stats_ponderadas,
            "temporadas_usadas": len(stats_por_temporada),
            "peso_actual": pesos[0],
            "total_partidos_historicos": total_partidos,
            "seasons": [s["season_id"] for s in stats_por_temporada]
        }
    
    def _calcular_pesos(self, n: int) -> List[float]:
        """
        Calcula pesos decrecientes para N temporadas.
        
        Temporada actual siempre tiene PESO_TEMPORADA_ACTUAL.
        El resto se reparte en PESO_HISTORICO.
        """
        if n == 1:
            return [1.0]
        
        pesos = [self.PESO_TEMPORADA_ACTUAL]
        peso_restante = self.PESO_HISTORICO
        
        # Distribuir peso histórico de forma decreciente
        for i in range(1, n):
            if i == n - 1:
                pesos.append(peso_restante)
            else:
                peso = peso_restante * 0.6  # 60% del restante
                pesos.append(peso)
                peso_restante -= peso
        
        return pesos
    
    async def obtener_h2h(
        self,
        equipo1: str,
        equipo2: str,
        liga_id: Optional[str] = None,
        limite: int = 10
    ) -> Dict[str, Any]:
        """
        Obtiene historial de enfrentamientos directos (Head to Head).
        
        Parámetros:
        -----------
        equipo1, equipo2 : str
            Nombres de los equipos
        liga_id : str, optional
            Filtrar por liga específica
        limite : int
            Máximo de partidos a considerar
        
        Retorna:
        --------
        Dict con estadísticas de enfrentamientos directos
        """
        # Buscar partidos entre estos dos equipos
        query = {
            "$or": [
                {"equipo_local": equipo1, "equipo_visitante": equipo2},
                {"equipo_local": equipo2, "equipo_visitante": equipo1}
            ],
            "estado_del_partido": "Match Finished"
        }
        
        if liga_id:
            query["liga_id"] = liga_id
        
        partidos = await self.db.football_matches.find(
            query,
            {"_id": 0}
        ).sort("fecha", -1).limit(limite).to_list(limite)
        
        if not partidos:
            return {
                "tiene_historial": False,
                "total_partidos": 0,
                "mensaje": "Sin enfrentamientos previos registrados"
            }
        
        # Analizar resultados
        victorias_eq1 = 0
        victorias_eq2 = 0
        empates = 0
        goles_eq1 = 0
        goles_eq2 = 0
        
        ultimos_resultados = []
        
        for p in partidos:
            g_local = p.get("goles_local_TR", 0) or 0
            g_visita = p.get("goles_visitante_TR", 0) or 0
            
            es_eq1_local = p["equipo_local"] == equipo1
            
            if es_eq1_local:
                goles_eq1 += g_local
                goles_eq2 += g_visita
                if g_local > g_visita:
                    victorias_eq1 += 1
                    ultimos_resultados.append(f"G {equipo1}")
                elif g_local < g_visita:
                    victorias_eq2 += 1
                    ultimos_resultados.append(f"G {equipo2}")
                else:
                    empates += 1
                    ultimos_resultados.append("E")
            else:
                goles_eq1 += g_visita
                goles_eq2 += g_local
                if g_visita > g_local:
                    victorias_eq1 += 1
                    ultimos_resultados.append(f"G {equipo1}")
                elif g_visita < g_local:
                    victorias_eq2 += 1
                    ultimos_resultados.append(f"G {equipo2}")
                else:
                    empates += 1
                    ultimos_resultados.append("E")
        
        total = len(partidos)
        
        return {
            "tiene_historial": True,
            "total_partidos": total,
            "equipo1": equipo1,
            "equipo2": equipo2,
            "victorias_eq1": victorias_eq1,
            "victorias_eq2": victorias_eq2,
            "empates": empates,
            "goles_eq1": goles_eq1,
            "goles_eq2": goles_eq2,
            "promedio_goles_total": round((goles_eq1 + goles_eq2) / total, 2) if total > 0 else 0,
            "porcentaje_eq1": round((victorias_eq1 / total) * 100, 1) if total > 0 else 0,
            "porcentaje_eq2": round((victorias_eq2 / total) * 100, 1) if total > 0 else 0,
            "porcentaje_empate": round((empates / total) * 100, 1) if total > 0 else 0,
            "ultimos_5": ultimos_resultados[:5],
            "tendencia": self._calcular_tendencia_h2h(victorias_eq1, victorias_eq2, empates, equipo1, equipo2)
        }
    
    def _calcular_tendencia_h2h(
        self,
        v1: int,
        v2: int,
        e: int,
        eq1: str,
        eq2: str
    ) -> Dict[str, Any]:
        """Calcula la tendencia del H2H."""
        total = v1 + v2 + e
        if total == 0:
            return {"tipo": "sin_datos", "descripcion": "Sin historial"}
        
        if v1 > v2 + e:
            return {
                "tipo": "dominante",
                "favorito": eq1,
                "descripcion": f"{eq1} domina el historial"
            }
        elif v2 > v1 + e:
            return {
                "tipo": "dominante",
                "favorito": eq2,
                "descripcion": f"{eq2} domina el historial"
            }
        elif e >= v1 and e >= v2:
            return {
                "tipo": "equilibrado",
                "favorito": None,
                "descripcion": "Historial muy equilibrado, muchos empates"
            }
        else:
            return {
                "tipo": "parejo",
                "favorito": None,
                "descripcion": "Historial parejo entre ambos"
            }
    
    async def calcular_factor_historico(
        self,
        equipo_local: str,
        equipo_visitante: str,
        liga_id: str,
        season_id_actual: str
    ) -> Dict[str, Any]:
        """
        Calcula factores de ajuste basados en histórico.
        
        Retorna factores que pueden usarse para ajustar probabilidades:
        - factor_historico_local: Ajuste para el local basado en historial
        - factor_historico_visita: Ajuste para visitante
        - factor_h2h: Ajuste basado en enfrentamientos directos
        """
        # Obtener stats históricas
        hist_local = await self.obtener_stats_historicas(equipo_local, liga_id, 3)
        hist_visita = await self.obtener_stats_historicas(equipo_visitante, liga_id, 3)
        
        # Obtener H2H
        h2h = await self.obtener_h2h(equipo_local, equipo_visitante, liga_id, 10)
        
        factores = {
            "factor_local": 1.0,
            "factor_visita": 1.0,
            "factor_h2h_local": 1.0,
            "factor_h2h_visita": 1.0,
            "h2h": h2h,
            "historico_local": hist_local,
            "historico_visita": hist_visita,
            "temporadas_analizadas": 0
        }
        
        # Ajustar por rendimiento histórico
        if hist_local and hist_local.get("temporadas_usadas", 0) > 1:
            rend_hist = hist_local["stats"].get("rendimiento_general", 50)
            # Bonus/penalización basado en rendimiento histórico
            factores["factor_local"] = 0.9 + (rend_hist / 500)  # 0.9 a 1.1
            factores["temporadas_analizadas"] = max(
                factores["temporadas_analizadas"],
                hist_local["temporadas_usadas"]
            )
        
        if hist_visita and hist_visita.get("temporadas_usadas", 0) > 1:
            rend_hist = hist_visita["stats"].get("rendimiento_general", 50)
            factores["factor_visita"] = 0.9 + (rend_hist / 500)
            factores["temporadas_analizadas"] = max(
                factores["temporadas_analizadas"],
                hist_visita["temporadas_usadas"]
            )
        
        # Ajustar por H2H
        if h2h.get("tiene_historial") and h2h.get("total_partidos", 0) >= 3:
            pct_local = h2h.get("porcentaje_eq1", 33)
            pct_visita = h2h.get("porcentaje_eq2", 33)
            
            # Ajuste suave basado en H2H (máximo ±10%)
            factores["factor_h2h_local"] = 0.95 + (pct_local / 1000)
            factores["factor_h2h_visita"] = 0.95 + (pct_visita / 1000)
        
        return factores
