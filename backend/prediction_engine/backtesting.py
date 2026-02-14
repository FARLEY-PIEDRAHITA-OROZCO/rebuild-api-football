"""
Motor de Backtesting - Validación histórica del sistema de pronósticos
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class BacktestingEngine:
    """Ejecuta backtesting contra partidos históricos."""
    
    def __init__(self, db):
        self.db = db
    
    async def ejecutar_backtesting(
        self,
        season_id: Optional[str] = None,
        liga_id: Optional[str] = None,
        limite: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta backtesting completo.
        
        Retorna métricas de precisión y ROI simulado.
        """
        from .stats_builder import StatsBuilder
        from .prediction_engine import PredictionEngine
        
        # Obtener partidos terminados
        query = {"estado_del_partido": "Match Finished"}
        if season_id:
            query["season_id"] = season_id
        elif liga_id:
            query["liga_id"] = liga_id
        
        partidos = await self.db.football_matches.find(
            query, {"_id": 0}
        ).sort("fecha", 1).to_list(limite or 10000)
        
        if not partidos:
            return {"error": "No hay partidos para analizar"}
        
        # Inicializar contadores
        resultados = {
            "total_partidos": len(partidos),
            "pronostico_principal": {"aciertos": 0, "total": 0},
            "doble_oportunidad": {"aciertos": 0, "total": 0},
            "ambos_marcan": {"aciertos": 0, "total": 0},
            "over_15": {"aciertos": 0, "total": 0},
            "over_25": {"aciertos": 0, "total": 0},
            "over_35": {"aciertos": 0, "total": 0},
            "roi_simulado": {"apuestas": 0, "ganancia": 0},
            "errores": 0,
            "detalle_errores": []
        }
        
        prediction_engine = PredictionEngine(self.db)
        
        for partido in partidos:
            try:
                resultado = await self._evaluar_partido(
                    partido, prediction_engine
                )
                self._acumular_resultado(resultados, resultado)
            except Exception as e:
                resultados["errores"] += 1
                if len(resultados["detalle_errores"]) < 5:
                    resultados["detalle_errores"].append(str(e)[:100])
        
        # Calcular porcentajes
        self._calcular_porcentajes(resultados)
        
        return resultados
    
    async def _evaluar_partido(
        self,
        partido: Dict,
        prediction_engine
    ) -> Dict[str, Any]:
        """Evalúa un partido individual."""
        
        equipo_local = partido["equipo_local"]
        equipo_visitante = partido["equipo_visitante"]
        liga_id = partido.get("liga_id")
        season_id = partido.get("season_id")
        
        # Resultado real
        goles_local = partido.get("goles_local_TR", 0)
        goles_visita = partido.get("goles_visitante_TR", 0)
        total_goles = goles_local + goles_visita
        
        # Determinar resultado real
        if goles_local > goles_visita:
            resultado_real = "L"
        elif goles_local < goles_visita:
            resultado_real = "V"
        else:
            resultado_real = "E"
        
        # Generar pronóstico
        pronostico = await prediction_engine.generar_pronostico(
            equipo_local=equipo_local,
            equipo_visitante=equipo_visitante,
            liga_id=liga_id,
            season_id=season_id
        )
        
        tc = pronostico.tiempo_completo
        
        # Evaluar pronóstico principal
        pronostico_principal = tc.pronostico
        acierto_principal = (pronostico_principal == resultado_real)
        
        # Evaluar doble oportunidad
        doble_op = tc.doble_oportunidad
        acierto_doble = self._evaluar_doble_oportunidad(doble_op, resultado_real)
        
        # Evaluar ambos marcan
        ambos_real = "SI" if (goles_local > 0 and goles_visita > 0) else "NO"
        acierto_ambos = (tc.ambos_marcan == ambos_real)
        
        # Evaluar Over/Under
        over_under = tc.over_under or {}
        acierto_over15 = self._evaluar_over(over_under.get("over_15", {}), total_goles, 1.5)
        acierto_over25 = self._evaluar_over(over_under.get("over_25", {}), total_goles, 2.5)
        acierto_over35 = self._evaluar_over(over_under.get("over_35", {}), total_goles, 3.5)
        
        return {
            "acierto_principal": acierto_principal,
            "acierto_doble": acierto_doble,
            "acierto_ambos": acierto_ambos,
            "acierto_over15": acierto_over15,
            "acierto_over25": acierto_over25,
            "acierto_over35": acierto_over35,
            "confianza": tc.confianza
        }
    
    def _evaluar_doble_oportunidad(self, prediccion: str, resultado: str) -> bool:
        """Evalúa si la doble oportunidad acertó."""
        if prediccion == "1X":
            return resultado in ["L", "E"]
        elif prediccion == "X2":
            return resultado in ["E", "V"]
        elif prediccion == "12":
            return resultado in ["L", "V"]
        return False
    
    def _evaluar_over(self, pred: Dict, total_goles: int, umbral: float) -> bool:
        """Evalúa predicción Over/Under."""
        if not pred:
            return False
        prediccion = pred.get("prediccion", "")
        real_over = total_goles > umbral
        return (prediccion == "OVER") == real_over
    
    def _acumular_resultado(self, resultados: Dict, resultado: Dict):
        """Acumula resultados de un partido."""
        resultados["pronostico_principal"]["total"] += 1
        resultados["doble_oportunidad"]["total"] += 1
        resultados["ambos_marcan"]["total"] += 1
        resultados["over_15"]["total"] += 1
        resultados["over_25"]["total"] += 1
        resultados["over_35"]["total"] += 1
        
        if resultado["acierto_principal"]:
            resultados["pronostico_principal"]["aciertos"] += 1
        if resultado["acierto_doble"]:
            resultados["doble_oportunidad"]["aciertos"] += 1
        if resultado["acierto_ambos"]:
            resultados["ambos_marcan"]["aciertos"] += 1
        if resultado["acierto_over15"]:
            resultados["over_15"]["aciertos"] += 1
        if resultado["acierto_over25"]:
            resultados["over_25"]["aciertos"] += 1
        if resultado["acierto_over35"]:
            resultados["over_35"]["aciertos"] += 1
        
        # ROI simulado (apuesta fija de 10€, cuota promedio 1.9)
        resultados["roi_simulado"]["apuestas"] += 10
        if resultado["acierto_doble"]:  # Usar doble oportunidad como base
            resultados["roi_simulado"]["ganancia"] += 10 * 1.4  # Cuota ~1.4 para doble op
    
    def _calcular_porcentajes(self, resultados: Dict):
        """Calcula porcentajes finales."""
        for key in ["pronostico_principal", "doble_oportunidad", "ambos_marcan", 
                    "over_15", "over_25", "over_35"]:
            total = resultados[key]["total"]
            if total > 0:
                pct = (resultados[key]["aciertos"] / total) * 100
                resultados[key]["porcentaje"] = round(pct, 2)
            else:
                resultados[key]["porcentaje"] = 0
        
        # ROI
        apuestas = resultados["roi_simulado"]["apuestas"]
        if apuestas > 0:
            ganancia = resultados["roi_simulado"]["ganancia"]
            roi = ((ganancia - apuestas) / apuestas) * 100
            resultados["roi_simulado"]["roi_porcentaje"] = round(roi, 2)
