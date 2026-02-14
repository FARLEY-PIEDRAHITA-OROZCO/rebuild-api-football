"""
========================================
MÓDULO: prediction_engine.py
========================================

Motor de Pronósticos - CORAZÓN DEL SISTEMA PLLA 3.0

Este módulo implementa el algoritmo principal de pronósticos,
equivalente a las hojas MAQUINA del Excel original.

Flujo del Algoritmo:
-------------------
1. Obtener estadísticas de ambos equipos
2. Calcular probabilidades base (L/E/V)
3. Aplicar factores de ajuste (1-5)
4. Ejecutar algoritmo de decisión
5. Generar doble oportunidad (1X/X2/12)
6. Calcular ambos marcan (SI/NO)
7. Calcular confianza del pronóstico

Clases:
-------
- PredictionEngine: Motor principal de pronósticos

Historial de Cambios:
--------------------
- v1.0.0 (Dic 2024): Versión inicial con algoritmo base del Excel
"""

from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timezone
import logging
import math

from .models import (
    Equipo,
    EstadisticasEquipo,
    Probabilidades,
    PronosticoTiempo,
    Pronostico
)
from .config import (
    Config,
    Umbrales,
    TipoTiempo,
    ResultadoEnum,
    DobleOportunidadEnum,
    AmbosMarcamEnum
)
from .stats_builder import StatsBuilder

logger = logging.getLogger(__name__)


class PredictionEngine:
    """
    Motor de Pronósticos Deportivos.
    
    Implementa el algoritmo PLLA 3.0 para generar pronósticos
    de partidos de fútbol basados en estadísticas históricas.
    
    Atributos:
    ----------
    db : AsyncIOMotorDatabase
        Conexión a MongoDB
    stats_builder : StatsBuilder
        Constructor de estadísticas
    umbrales : Umbrales
        Umbrales del algoritmo
    
    Métodos Públicos:
    ----------------
    generar_pronostico(equipo_local, equipo_visitante, liga_id)
        Genera pronóstico completo para un partido
    
    generar_pronostico_tiempo(stats_local, stats_visita, tipo_tiempo)
        Genera pronóstico para un tiempo específico
    
    Ejemplo de Uso:
    ---------------
    ```python
    engine = PredictionEngine(db)
    pronostico = await engine.generar_pronostico(
        equipo_local='Barcelona',
        equipo_visitante='Real Madrid',
        liga_id='SPAIN_LA_LIGA'
    )
    
    print(pronostico.tiempo_completo.pronostico)  # "L"
    print(pronostico.tiempo_completo.doble_oportunidad)  # "1X"
    print(pronostico.tiempo_completo.probabilidades.porcentaje_local)  # 55.3
    ```
    """
    
    def __init__(self, db, usar_historico: bool = True):
        """
        Inicializa el motor de pronósticos.
        
        Parámetros:
        -----------
        db : AsyncIOMotorDatabase
            Conexión a MongoDB
        usar_historico : bool
            Si True, usa datos históricos de múltiples temporadas (default: True)
        """
        self.db = db
        self.stats_builder = StatsBuilder(db)
        self.umbrales = Umbrales()
        self.usar_historico = usar_historico
        
        # Importar aquí para evitar circular imports
        from .historico_consolidado import HistoricoConsolidado
        self.historico = HistoricoConsolidado(db)
        
        logger.info(f"PredictionEngine inicializado - v{Config.VERSION} (histórico={'ON' if usar_historico else 'OFF'})")
    
    async def generar_pronostico(
        self,
        equipo_local: str,
        equipo_visitante: str,
        liga_id: str,
        temporada: Optional[int] = None,
        season_id: Optional[str] = None,
        partido_id: Optional[str] = None
    ) -> Pronostico:
        """
        Genera pronóstico completo para un partido.
        
        Incluye pronósticos para:
        - Tiempo Completo (90 min)
        - Primer Tiempo (1MT)
        - Segundo Tiempo (2MT)
        - Over/Under goles
        - Forma reciente de los equipos
        
        Parámetros:
        -----------
        equipo_local : str
            Nombre del equipo local
        equipo_visitante : str
            Nombre del equipo visitante
        liga_id : str
            ID de la liga
        temporada : int, optional
            Año de la temporada (legacy)
        season_id : str, optional
            ID de temporada estructurado (preferido)
        partido_id : str, optional
            ID del partido (para tracking)
        
        Retorna:
        --------
        Pronostico
            Objeto con pronósticos para los 3 tiempos
        
        Raises:
        -------
        ValueError
            Si no se encuentran estadísticas de algún equipo
        """
        logger.info(f"Generando pronóstico: {equipo_local} vs {equipo_visitante}, season_id={season_id}")
        
        # Obtener estadísticas de ambos equipos
        stats_local = await self.stats_builder.obtener_stats_equipo(
            equipo_local, liga_id, temporada, season_id
        )
        stats_visitante = await self.stats_builder.obtener_stats_equipo(
            equipo_visitante, liga_id, temporada, season_id
        )
        
        # Validar que existen estadísticas
        if not stats_local:
            raise ValueError(f"No se encontraron estadísticas para {equipo_local}")
        if not stats_visitante:
            raise ValueError(f"No se encontraron estadísticas para {equipo_visitante}")
        
        # Obtener forma reciente de ambos equipos
        forma_local = await self.stats_builder.obtener_forma_reciente(
            equipo_local, liga_id, season_id, temporada
        )
        forma_visitante = await self.stats_builder.obtener_forma_reciente(
            equipo_visitante, liga_id, season_id, temporada
        )
        
        # Obtener factores históricos (H2H + múltiples temporadas)
        factores_historicos = None
        if self.usar_historico:
            try:
                factores_historicos = await self.historico.calcular_factor_historico(
                    equipo_local, equipo_visitante, liga_id, season_id
                )
                logger.debug(f"Factores históricos obtenidos: {factores_historicos.get('temporadas_analizadas', 0)} temporadas, H2H: {factores_historicos.get('h2h', {}).get('tiene_historial', False)}")
            except Exception as e:
                logger.warning(f"Error obteniendo factores históricos: {e}")
                factores_historicos = None
        
        # Generar pronóstico para cada tiempo
        pronostico_tc = self._generar_pronostico_tiempo(
            stats_local.stats_completo,
            stats_visitante.stats_completo,
            TipoTiempo.COMPLETO,
            forma_local,
            forma_visitante,
            factores_historicos
        )
        
        pronostico_1mt = self._generar_pronostico_tiempo(
            stats_local.stats_primer_tiempo,
            stats_visitante.stats_primer_tiempo,
            TipoTiempo.PRIMER_TIEMPO,
            forma_local,
            forma_visitante,
            factores_historicos
        )
        
        pronostico_2mt = self._generar_pronostico_tiempo(
            stats_local.stats_segundo_tiempo,
            stats_visitante.stats_segundo_tiempo,
            TipoTiempo.SEGUNDO_TIEMPO,
            forma_local,
            forma_visitante,
            factores_historicos
        )
        
        # Crear pronóstico completo
        h2h_info = factores_historicos.get("h2h") if factores_historicos else None
        
        pronostico = Pronostico(
            partido_id=partido_id,
            equipo_local=equipo_local,
            equipo_visitante=equipo_visitante,
            liga_id=liga_id,
            season_id=season_id,
            tiempo_completo=pronostico_tc,
            primer_tiempo=pronostico_1mt,
            segundo_tiempo=pronostico_2mt,
            forma_reciente={
                "local": forma_local,
                "visitante": forma_visitante
            },
            h2h=h2h_info,
            temporadas_analizadas=factores_historicos.get("temporadas_analizadas", 1) if factores_historicos else 1,
            version_algoritmo=Config.VERSION
        )
        
        # Guardar en base de datos
        await self._guardar_pronostico(pronostico)
        
        logger.info(f"Pronóstico generado: TC={pronostico_tc.pronostico}, "
                   f"1MT={pronostico_1mt.pronostico}, 2MT={pronostico_2mt.pronostico}")
        
        return pronostico
    
    def _generar_pronostico_tiempo(
        self,
        stats_local: EstadisticasEquipo,
        stats_visitante: EstadisticasEquipo,
        tipo_tiempo: TipoTiempo,
        forma_local: Dict[str, Any] = None,
        forma_visitante: Dict[str, Any] = None,
        factores_historicos: Dict[str, Any] = None
    ) -> PronosticoTiempo:
        """
        Genera pronóstico para un tiempo específico.
        
        Este método ejecuta el algoritmo principal:
        1. Calcular probabilidades
        2. Calcular factores de ajuste
        3. Aplicar ajuste por forma reciente
        4. Aplicar ajuste por histórico (H2H + múltiples temporadas)
        5. Aplicar algoritmo de decisión
        6. Generar doble oportunidad
        7. Calcular ambos marcan
        8. Calcular Over/Under goles
        9. Calcular confianza
        
        Parámetros:
        -----------
        stats_local : EstadisticasEquipo
            Estadísticas del equipo local
        stats_visitante : EstadisticasEquipo
            Estadísticas del equipo visitante
        tipo_tiempo : TipoTiempo
            Tipo de tiempo (TC, 1MT, 2MT)
        forma_local : dict, optional
            Forma reciente del equipo local
        forma_visitante : dict, optional
            Forma reciente del equipo visitante
        factores_historicos : dict, optional
            Factores de ajuste basados en histórico y H2H
        
        Retorna:
        --------
        PronosticoTiempo
            Pronóstico para el tiempo especificado
        """
        # PASO 1: Calcular probabilidades base
        probabilidades = self._calcular_probabilidades(
            stats_local, stats_visitante
        )
        
        # PASO 2: Calcular factores de ajuste
        factor_local = self._calcular_factor_ajuste(stats_local.rendimiento_local)
        factor_visita = self._calcular_factor_ajuste(stats_visitante.rendimiento_visita)
        
        # PASO 3: Ajustar por forma reciente si está disponible
        if forma_local and forma_visitante:
            probabilidades = self._ajustar_por_forma_reciente(
                probabilidades, forma_local, forma_visitante
            )
        
        # PASO 4: Ajustar por histórico (H2H + múltiples temporadas)
        if factores_historicos:
            probabilidades = self._ajustar_por_historico(
                probabilidades, factores_historicos
            )
            # Ajustar factores locales también
            factor_local *= factores_historicos.get("factor_local", 1.0)
            factor_visita *= factores_historicos.get("factor_visita", 1.0)
        
        # PASO 5: Aplicar algoritmo de decisión
        pronostico = self._aplicar_algoritmo_decision(
            probabilidades, factor_local, factor_visita
        )
        
        # PASO 6: Generar doble oportunidad
        doble_oportunidad = self._generar_doble_oportunidad(
            pronostico, probabilidades
        )
        
        # PASO 7: Calcular ambos marcan
        ambos_marcan = self._calcular_ambos_marcan(
            stats_local, stats_visitante
        )
        
        # PASO 8: Calcular Over/Under y goles esperados
        over_under, goles_esperados = self._calcular_over_under(
            stats_local, stats_visitante, forma_local, forma_visitante, tipo_tiempo
        )
        
        # PASO 9: Calcular confianza (ahora incluye bonus por histórico)
        confianza = self._calcular_confianza(
            probabilidades, pronostico, factor_local, factor_visita
        )
        
        return PronosticoTiempo(
            pronostico=pronostico,
            doble_oportunidad=doble_oportunidad,
            ambos_marcan=ambos_marcan,
            probabilidades=probabilidades,
            confianza=confianza,
            factor_local=factor_local,
            factor_visita=factor_visita,
            over_under=over_under,
            goles_esperados=goles_esperados
        )
    
    def _calcular_probabilidades(
        self,
        stats_local: EstadisticasEquipo,
        stats_visitante: EstadisticasEquipo
    ) -> Probabilidades:
        """
        Calcula las probabilidades base de L/E/V.
        
        Lógica:
        -------
        - El rendimiento LOCAL se mide con stats como LOCAL
        - El rendimiento VISITA se mide con stats como VISITANTE
        - La probabilidad es proporcional al rendimiento
        - El empate se calcula según la cercanía de fuerzas
        
        Parámetros:
        -----------
        stats_local : EstadisticasEquipo
            Stats del equipo que juega de local
        stats_visitante : EstadisticasEquipo
            Stats del equipo que juega de visitante
        
        Retorna:
        --------
        Probabilidades
            Porcentajes de L/E/V
        
        Fórmulas:
        ---------
        rendimiento = (puntos / puntos_posibles) * 100
        
        prob_local = rend_local_L / (rend_local_L + rend_visita_V) * 100
        prob_visita = rend_visita_V / (rend_local_L + rend_visita_V) * 100
        
        factor_empate = max(0, 30 - |prob_local - prob_visita|)
        """
        # Obtener rendimientos específicos
        # El LOCAL usa su rendimiento COMO LOCAL
        rend_local = stats_local.rendimiento_local
        # El VISITANTE usa su rendimiento COMO VISITANTE
        rend_visita = stats_visitante.rendimiento_visita
        
        # Si no hay datos suficientes, usar promedios por defecto
        if stats_local.pj_local < Config.MIN_PARTIDOS_CONFIABLE:
            rend_local = Config.PROMEDIOS_POR_DEFECTO['prob_local']
        
        if stats_visitante.pj_visita < Config.MIN_PARTIDOS_CONFIABLE:
            rend_visita = Config.PROMEDIOS_POR_DEFECTO['prob_visita']
        
        # Calcular suma total para normalizar
        total = rend_local + rend_visita
        
        if total == 0:
            # Sin datos, usar promedios históricos
            return Probabilidades(
                porcentaje_local=Config.PROMEDIOS_POR_DEFECTO['prob_local'],
                porcentaje_empate=Config.PROMEDIOS_POR_DEFECTO['prob_empate'],
                porcentaje_visita=Config.PROMEDIOS_POR_DEFECTO['prob_visita']
            )
        
        # Probabilidades base proporcionales al rendimiento
        prob_local_base = (rend_local / total) * 100
        prob_visita_base = (rend_visita / total) * 100
        
        # Calcular factor de empate
        # Cuando las probabilidades son cercanas, más probable el empate
        diferencia = abs(prob_local_base - prob_visita_base)
        
        # Factor de empate: máximo 30% cuando equipos muy parejos
        # Se reduce proporcionalmente a la diferencia
        factor_empate = max(0, 30 - diferencia)
        
        # Ajustar probabilidades considerando el empate
        # El empate "toma" porcentaje de ambos equipos
        prob_empate = factor_empate
        
        # Redistribuir el resto entre local y visita
        resto = 100 - factor_empate
        prob_local = prob_local_base * resto / 100
        prob_visita = prob_visita_base * resto / 100
        
        # Normalizar para que sume exactamente 100%
        suma = prob_local + prob_empate + prob_visita
        
        return Probabilidades(
            porcentaje_local=round(prob_local / suma * 100, 2),
            porcentaje_empate=round(prob_empate / suma * 100, 2),
            porcentaje_visita=round(prob_visita / suma * 100, 2)
        )
    
    def _calcular_factor_ajuste(self, rendimiento: float) -> int:
        """
        Convierte rendimiento porcentual a factor de ajuste (1-5).
        
        El factor pondera la "fuerza" del equipo:
        - 5: Equipo dominante (>80%)
        - 4: Equipo fuerte (60-80%)
        - 3: Equipo promedio (40-60%)
        - 2: Equipo débil (20-40%)
        - 1: Equipo muy débil (<20%)
        
        Parámetros:
        -----------
        rendimiento : float
            Rendimiento porcentual (0-100)
        
        Retorna:
        --------
        int
            Factor de ajuste (1-5)
        
        Ejemplo:
        --------
        ```python
        factor = engine._calcular_factor_ajuste(75.5)
        print(factor)  # 4
        ```
        """
        if rendimiento > Umbrales.FACTOR_5_MIN:
            return 5
        elif rendimiento > Umbrales.FACTOR_4_MIN:
            return 4
        elif rendimiento > Umbrales.FACTOR_3_MIN:
            return 3
        elif rendimiento > Umbrales.FACTOR_2_MIN:
            return 2
        else:
            return 1
    
    def _aplicar_algoritmo_decision(
        self,
        probabilidades: Probabilidades,
        factor_local: int,
        factor_visita: int
    ) -> str:
        """
        Algoritmo principal de decisión.
        
        Implementa las reglas del Excel PLLA 3.0 para determinar
        el resultado más probable del partido.
        
        Parámetros:
        -----------
        probabilidades : Probabilidades
            Porcentajes calculados
        factor_local : int
            Factor de ajuste del local (1-5)
        factor_visita : int
            Factor de ajuste del visitante (1-5)
        
        Retorna:
        --------
        str
            "L" (Local), "E" (Empate) o "V" (Visita)
        
        Reglas de Decisión:
        -------------------
        1. REGLA LOCAL CLARO:
           Si prob_local está en rango óptimo (43-69.5%) y empate bajo (<20%)
           → LOCAL
        
        2. REGLA VISITA:
           Si prob_local < umbral mínimo y prob_visita > prob_local
           → VISITA
        
        3. REGLA EMPATE:
           Si prob_empate >= 20% y equipos muy parejos
           → EMPATE
        
        4. REGLA LOCAL MUY FAVORITO:
           Si prob_local >= 69.5%
           → LOCAL
        
        5. REGLA POR DEFECTO:
           El de mayor probabilidad gana
        """
        p_local = probabilidades.porcentaje_local
        p_empate = probabilidades.porcentaje_empate
        p_visita = probabilidades.porcentaje_visita
        
        # Aplicar ponderación por factores
        # Un factor mayor aumenta ligeramente la probabilidad
        ajuste_local = (factor_local - 3) * 2  # -4 a +4
        ajuste_visita = (factor_visita - 3) * 2
        
        p_local_ajustado = p_local + ajuste_local
        p_visita_ajustado = p_visita + ajuste_visita
        
        # REGLA 1: Local claro favorito (rango óptimo)
        if (Umbrales.PROB_LOCAL_MIN < p_local_ajustado < Umbrales.PROB_LOCAL_MAX 
            and p_empate < Umbrales.PROB_EMPATE_MAX):
            return ResultadoEnum.LOCAL.value
        
        # REGLA 2: Local muy favorito (sobre el máximo)
        if p_local_ajustado >= Umbrales.PROB_LOCAL_MAX:
            return ResultadoEnum.LOCAL.value
        
        # REGLA 3: Visita favorito
        if (p_local_ajustado < Umbrales.PROB_LOCAL_MIN 
            and p_visita_ajustado > p_local_ajustado):
            return ResultadoEnum.VISITA.value
        
        # REGLA 4: Empate probable (equipos parejos)
        if p_empate >= Umbrales.PROB_EMPATE_MAX:
            diferencia = abs(p_local_ajustado - p_visita_ajustado)
            if diferencia < Umbrales.DIFERENCIA_EMPATE:
                return ResultadoEnum.EMPATE.value
        
        # REGLA 5: Por defecto, el de mayor probabilidad
        if p_local_ajustado >= p_visita_ajustado and p_local_ajustado >= p_empate:
            return ResultadoEnum.LOCAL.value
        elif p_visita_ajustado >= p_local_ajustado and p_visita_ajustado >= p_empate:
            return ResultadoEnum.VISITA.value
        else:
            return ResultadoEnum.EMPATE.value
    
    def _generar_doble_oportunidad(
        self,
        pronostico: str,
        probabilidades: Probabilidades
    ) -> str:
        """
        Genera la apuesta de doble oportunidad.
        
        La doble oportunidad cubre 2 de 3 resultados:
        - 1X: Local o Empate (excluye Visita)
        - X2: Empate o Visita (excluye Local)
        - 12: Local o Visita (excluye Empate)
        
        Parámetros:
        -----------
        pronostico : str
            Pronóstico principal (L/E/V)
        probabilidades : Probabilidades
            Porcentajes calculados
        
        Retorna:
        --------
        str
            "1X", "X2" o "12"
        
        Lógica:
        -------
        - Si la suma de local+visita es alta (>116%), el empate es improbable
          → 12 (cualquiera gana)
        
        - Si el pronóstico es LOCAL, cubrir con empate → 1X
        - Si el pronóstico es VISITA, cubrir con empate → X2
        - Si el pronóstico es EMPATE, cubrir con el segundo favorito
        """
        p_local = probabilidades.porcentaje_local
        p_visita = probabilidades.porcentaje_visita
        
        # Suma sin empate (local + visita, excluyendo empate)
        suma_sin_empate = p_local + p_visita
        
        # REGLA 1: Si suma sin empate es alta, apostar "12"
        # Esto indica que el empate es poco probable
        if suma_sin_empate > Umbrales.SUMA_PROB_MIN:
            return DobleOportunidadEnum.LOCAL_VISITA.value
        
        # REGLA 2: Basarse en el pronóstico principal
        if pronostico == ResultadoEnum.LOCAL.value:
            # Local favorito, cubrir con empate
            return DobleOportunidadEnum.LOCAL_EMPATE.value
        
        elif pronostico == ResultadoEnum.VISITA.value:
            # Visita favorito, cubrir con empate
            return DobleOportunidadEnum.EMPATE_VISITA.value
        
        else:  # Empate
            # Ver cuál es el segundo favorito
            if p_local > p_visita:
                return DobleOportunidadEnum.LOCAL_EMPATE.value
            else:
                return DobleOportunidadEnum.EMPATE_VISITA.value
    
    def _calcular_ambos_marcan(
        self,
        stats_local: EstadisticasEquipo,
        stats_visitante: EstadisticasEquipo
    ) -> str:
        """
        Determina si ambos equipos marcarán.
        
        Basado en:
        - Capacidad ofensiva de cada equipo
        - Debilidad defensiva del rival
        
        Parámetros:
        -----------
        stats_local : EstadisticasEquipo
            Stats del local
        stats_visitante : EstadisticasEquipo
            Stats del visitante
        
        Retorna:
        --------
        str
            "SI" o "NO"
        
        Lógica:
        -------
        prob_local_marca = (avg_gf_local + avg_gc_visita) / 2
        prob_visita_marca = (avg_gf_visita + avg_gc_local) / 2
        prob_ambos = prob_local_marca * prob_visita_marca * factor
        
        Si prob_ambos > umbral → SI
        Si no → NO
        """
        # Promedios de goles del local (jugando en casa)
        if stats_local.pj_local > 0:
            avg_gf_local = stats_local.gf_local / stats_local.pj_local
            avg_gc_local = stats_local.gc_local / stats_local.pj_local
        else:
            avg_gf_local = Config.PROMEDIOS_POR_DEFECTO['goles_local']
            avg_gc_local = Config.PROMEDIOS_POR_DEFECTO['goles_visita']
        
        # Promedios de goles del visitante (jugando fuera)
        if stats_visitante.pj_visita > 0:
            avg_gf_visita = stats_visitante.gf_visita / stats_visitante.pj_visita
            avg_gc_visita = stats_visitante.gc_visita / stats_visitante.pj_visita
        else:
            avg_gf_visita = Config.PROMEDIOS_POR_DEFECTO['goles_visita']
            avg_gc_visita = Config.PROMEDIOS_POR_DEFECTO['goles_local']
        
        # Probabilidad de que el local marque
        # Combina su capacidad ofensiva + debilidad defensiva rival
        prob_local_marca = (avg_gf_local + avg_gc_visita) / 2
        
        # Probabilidad de que la visita marque
        prob_visita_marca = (avg_gf_visita + avg_gc_local) / 2
        
        # Probabilidad combinada de que ambos marquen
        # Normalizada a porcentaje (0-100)
        prob_ambos = (prob_local_marca * prob_visita_marca) / 2 * 100
        
        # Aplicar umbral
        if prob_ambos > Umbrales.UMBRAL_AMBOS_MARCAN:
            return AmbosMarcamEnum.SI.value
        else:
            return AmbosMarcamEnum.NO.value
    
    def _ajustar_por_forma_reciente(
        self,
        probabilidades: Probabilidades,
        forma_local: Dict[str, Any],
        forma_visitante: Dict[str, Any]
    ) -> Probabilidades:
        """
        Ajusta las probabilidades basándose en la forma reciente.
        
        Parámetros:
        -----------
        probabilidades : Probabilidades
            Probabilidades base calculadas
        forma_local : dict
            Forma reciente del equipo local
        forma_visitante : dict
            Forma reciente del equipo visitante
        
        Retorna:
        --------
        Probabilidades
            Probabilidades ajustadas por forma reciente
        """
        peso = Umbrales.PESO_FORMA_RECIENTE  # 0.3 por defecto
        
        # Obtener rendimientos de forma reciente
        rend_forma_local = forma_local.get('rendimiento', 50.0)
        rend_forma_visitante = forma_visitante.get('rendimiento', 50.0)
        
        # Normalizar a factor de ajuste (-1 a 1)
        factor_local = (rend_forma_local - 50) / 50  # -1 si 0%, +1 si 100%
        factor_visitante = (rend_forma_visitante - 50) / 50
        
        # Ajustar probabilidades
        p_local = probabilidades.porcentaje_local
        p_visita = probabilidades.porcentaje_visita
        
        # Aplicar ajustes ponderados
        ajuste_local = factor_local * peso * 10  # Máximo ±3% de ajuste
        ajuste_visitante = factor_visitante * peso * 10
        
        p_local_ajustado = max(5, min(90, p_local + ajuste_local))
        p_visita_ajustado = max(5, min(90, p_visita + ajuste_visitante))
        
        # Recalcular empate para que sumen 100
        p_empate_ajustado = 100 - p_local_ajustado - p_visita_ajustado
        p_empate_ajustado = max(5, min(50, p_empate_ajustado))
        
        # Normalizar para que sumen exactamente 100
        total = p_local_ajustado + p_empate_ajustado + p_visita_ajustado
        p_local_ajustado = p_local_ajustado / total * 100
        p_empate_ajustado = p_empate_ajustado / total * 100
        p_visita_ajustado = p_visita_ajustado / total * 100
        
        return Probabilidades(
            porcentaje_local=round(p_local_ajustado, 2),
            porcentaje_empate=round(p_empate_ajustado, 2),
            porcentaje_visita=round(p_visita_ajustado, 2)
        )
    
    def _ajustar_por_historico(
        self,
        probabilidades: Probabilidades,
        factores_historicos: Dict[str, Any]
    ) -> Probabilidades:
        """
        Ajusta las probabilidades basándose en histórico y H2H.
        
        Parámetros:
        -----------
        probabilidades : Probabilidades
            Probabilidades base calculadas
        factores_historicos : dict
            Factores de ajuste histórico incluyendo H2H
        
        Retorna:
        --------
        Probabilidades
            Probabilidades ajustadas por histórico
        """
        p_local = probabilidades.porcentaje_local
        p_empate = probabilidades.porcentaje_empate
        p_visita = probabilidades.porcentaje_visita
        
        # Factor H2H (enfrentamientos directos)
        h2h = factores_historicos.get("h2h", {})
        if h2h.get("tiene_historial") and h2h.get("total_partidos", 0) >= 3:
            # Ajustar según historial de enfrentamientos
            pct_eq1 = h2h.get("porcentaje_eq1", 33)  # Local
            pct_eq2 = h2h.get("porcentaje_eq2", 33)  # Visitante
            pct_e = h2h.get("porcentaje_empate", 33)
            
            # Peso del H2H (20% de influencia)
            peso_h2h = 0.20
            
            # Mezclar probabilidades actuales con H2H
            p_local = p_local * (1 - peso_h2h) + pct_eq1 * peso_h2h
            p_visita = p_visita * (1 - peso_h2h) + pct_eq2 * peso_h2h
            p_empate = p_empate * (1 - peso_h2h) + pct_e * peso_h2h
        
        # Factor de temporadas históricas
        factor_local = factores_historicos.get("factor_local", 1.0)
        factor_visita = factores_historicos.get("factor_visita", 1.0)
        
        # Aplicar factores (ajuste suave)
        p_local *= factor_local
        p_visita *= factor_visita
        
        # Normalizar para que sumen 100
        total = p_local + p_empate + p_visita
        p_local = p_local / total * 100
        p_empate = p_empate / total * 100
        p_visita = p_visita / total * 100
        
        return Probabilidades(
            porcentaje_local=round(p_local, 2),
            porcentaje_empate=round(p_empate, 2),
            porcentaje_visita=round(p_visita, 2)
        )
    
    def _calcular_over_under(
        self,
        stats_local: EstadisticasEquipo,
        stats_visitante: EstadisticasEquipo,
        forma_local: Dict[str, Any],
        forma_visitante: Dict[str, Any],
        tipo_tiempo: TipoTiempo
    ) -> Tuple[Dict[str, Any], Dict[str, float]]:
        """
        Calcula predicciones de Over/Under y goles esperados.
        
        Parámetros:
        -----------
        stats_local : EstadisticasEquipo
            Estadísticas del equipo local
        stats_visitante : EstadisticasEquipo
            Estadísticas del equipo visitante
        forma_local : dict
            Forma reciente del local
        forma_visitante : dict
            Forma reciente del visitante
        tipo_tiempo : TipoTiempo
            Tipo de tiempo (TC, 1MT, 2MT)
        
        Retorna:
        --------
        Tuple[Dict, Dict]
            (over_under, goles_esperados)
        """
        # Calcular promedios de goles
        if stats_local.pj_local > 0:
            avg_gf_local = stats_local.gf_local / stats_local.pj_local
            avg_gc_local = stats_local.gc_local / stats_local.pj_local
        else:
            avg_gf_local = 1.3
            avg_gc_local = 1.0
        
        if stats_visitante.pj_visita > 0:
            avg_gf_visita = stats_visitante.gf_visita / stats_visitante.pj_visita
            avg_gc_visita = stats_visitante.gc_visita / stats_visitante.pj_visita
        else:
            avg_gf_visita = 0.9
            avg_gc_visita = 1.5
        
        # Goles esperados por equipo
        # Local: (su promedio goleador + debilidad defensiva rival) / 2
        goles_local = (avg_gf_local + avg_gc_visita) / 2
        # Visitante: (su promedio goleador fuera + debilidad defensiva local) / 2
        goles_visitante = (avg_gf_visita + avg_gc_local) / 2
        
        # Ajustar por forma reciente si está disponible
        if forma_local and forma_visitante:
            goles_local_forma = forma_local.get('goles_favor_avg', goles_local)
            goles_visitante_forma = forma_visitante.get('goles_favor_avg', goles_visitante)
            
            peso_forma = Umbrales.PESO_FORMA_RECIENTE
            goles_local = goles_local * (1 - peso_forma) + goles_local_forma * peso_forma
            goles_visitante = goles_visitante * (1 - peso_forma) + goles_visitante_forma * peso_forma
        
        # Ajustar por tipo de tiempo
        if tipo_tiempo == TipoTiempo.PRIMER_TIEMPO:
            factor_tiempo = 0.45  # 45% de goles en 1MT típicamente
        elif tipo_tiempo == TipoTiempo.SEGUNDO_TIEMPO:
            factor_tiempo = 0.55  # 55% de goles en 2MT típicamente
        else:
            factor_tiempo = 1.0
        
        goles_local = goles_local * factor_tiempo
        goles_visitante = goles_visitante * factor_tiempo
        total_esperado = goles_local + goles_visitante
        
        # Calcular probabilidades Over/Under usando distribución de Poisson simplificada
        over_under = {}
        
        for umbral, nombre in [(1.5, "over_15"), (2.5, "over_25"), (3.5, "over_35")]:
            # Probabilidad aproximada usando media esperada
            prob_over = self._calcular_prob_over(total_esperado, umbral)
            prediccion = "OVER" if prob_over > 50 else "UNDER"
            over_under[nombre] = {
                "prediccion": prediccion,
                "probabilidad": round(prob_over if prediccion == "OVER" else 100 - prob_over, 2)
            }
        
        goles_esperados = {
            "local": round(goles_local, 2),
            "visitante": round(goles_visitante, 2),
            "total": round(total_esperado, 2)
        }
        
        return over_under, goles_esperados
    
    def _calcular_prob_over(self, media: float, umbral: float) -> float:
        """
        Calcula la probabilidad de Over usando aproximación de Poisson.
        
        P(X > umbral) ≈ 1 - P(X <= umbral)
        Usando aproximación simplificada basada en la media.
        """
        
        # Probabilidad acumulada P(X <= k) usando Poisson
        prob_under = 0
        k = 0
        umbral_int = int(umbral)
        
        while k <= umbral_int:
            # P(X = k) = (λ^k * e^-λ) / k!
            try:
                p_k = (media ** k) * math.exp(-media) / math.factorial(k)
                prob_under += p_k
            except (OverflowError, ValueError):
                break
            k += 1
        
        prob_over = (1 - prob_under) * 100
        return max(5, min(95, prob_over))  # Limitar entre 5% y 95%
    
    def _calcular_confianza(
        self,
        probabilidades: Probabilidades,
        pronostico: str,
        factor_local: int,
        factor_visita: int
    ) -> float:
        """
        Calcula el nivel de confianza del pronóstico.
        
        La confianza indica qué tan seguro es el pronóstico
        basado en:
        - Diferencia de probabilidades
        - Factores de ajuste
        - Claridad del resultado
        
        Parámetros:
        -----------
        probabilidades : Probabilidades
            Porcentajes calculados
        pronostico : str
            Pronóstico principal
        factor_local : int
            Factor del local
        factor_visita : int
            Factor del visitante
        
        Retorna:
        --------
        float
            Confianza (0-100)
        
        Lógica:
        -------
        - Confianza base = probabilidad del resultado pronosticado
        - Ajuste por diferencia de factores
        - Ajuste por claridad (diferencia entre primero y segundo)
        """
        p_local = probabilidades.porcentaje_local
        p_empate = probabilidades.porcentaje_empate
        p_visita = probabilidades.porcentaje_visita
        
        # Confianza base: probabilidad del resultado pronosticado
        if pronostico == ResultadoEnum.LOCAL.value:
            confianza_base = p_local
        elif pronostico == ResultadoEnum.VISITA.value:
            confianza_base = p_visita
        else:
            confianza_base = p_empate
        
        # Ordenar probabilidades para calcular claridad
        probs = sorted([p_local, p_empate, p_visita], reverse=True)
        diferencia_top = probs[0] - probs[1]  # Diferencia entre 1ro y 2do
        
        # Ajuste por claridad: más diferencia = más confianza
        ajuste_claridad = min(diferencia_top * 0.5, 15)  # Máximo +15
        
        # Ajuste por factores: si el favorito tiene mejor factor
        if pronostico == ResultadoEnum.LOCAL.value:
            ajuste_factor = (factor_local - factor_visita) * 2
        elif pronostico == ResultadoEnum.VISITA.value:
            ajuste_factor = (factor_visita - factor_local) * 2
        else:
            ajuste_factor = -abs(factor_local - factor_visita)  # Empate prefiere igualdad
        
        # Calcular confianza final
        confianza = confianza_base + ajuste_claridad + ajuste_factor
        
        # Limitar a rango 0-100
        return round(max(0, min(100, confianza)), 2)
    
    async def _guardar_pronostico(self, pronostico: Pronostico) -> None:
        """
        Guarda el pronóstico en la base de datos.
        
        Parámetros:
        -----------
        pronostico : Pronostico
            Pronóstico a guardar
        """
        collection = self.db[Config.COLECCION_PRONOSTICOS]
        
        # Convertir a dict
        pronostico_dict = pronostico.model_dump()
        
        # Insertar
        await collection.insert_one(pronostico_dict)
        
        logger.debug(f"Pronóstico guardado: {pronostico.id}")
