"""
========================================
MÓDULO: config.py
========================================

Configuración y umbrales del Motor de Pronósticos PLLA 3.0.

Este archivo contiene todas las constantes y umbrales utilizados
en el algoritmo de pronósticos. Los valores fueron extraídos del
Excel original y pueden ser ajustados para optimización.

IMPORTANTE:
-----------
Modificar estos valores afectará directamente los pronósticos.
Cualquier cambio debe ser documentado y probado exhaustivamente.

Historial de Cambios:
--------------------
- v1.0.0 (Dic 2024): Valores originales del Excel PLLA 3.0
"""

from enum import Enum
from typing import Dict, Any


# ============================================
# ENUMERACIONES
# ============================================

class TipoTiempo(str, Enum):
    """
    Tipos de tiempo para análisis.
    
    - COMPLETO: 90 minutos (Tiempo Reglamentario)
    - PRIMER_TIEMPO: Primeros 45 minutos (1MT)
    - SEGUNDO_TIEMPO: Últimos 45 minutos (2MT)
    """
    COMPLETO = "completo"
    PRIMER_TIEMPO = "primer_tiempo"
    SEGUNDO_TIEMPO = "segundo_tiempo"


class ResultadoEnum(str, Enum):
    """
    Posibles resultados de un partido.
    
    - LOCAL: Gana el equipo local
    - EMPATE: Empate
    - VISITA: Gana el equipo visitante
    """
    LOCAL = "L"
    EMPATE = "E"
    VISITA = "V"


class DobleOportunidadEnum(str, Enum):
    """
    Opciones de doble oportunidad.
    
    - 1X: Local o Empate (cubre 2 de 3 resultados)
    - X2: Empate o Visita
    - 12: Local o Visita (sin empate)
    """
    LOCAL_EMPATE = "1X"
    EMPATE_VISITA = "X2"
    LOCAL_VISITA = "12"


class AmbosMarcamEnum(str, Enum):
    """
    Opciones para ambos marcan.
    
    - SI: Ambos equipos marcarán al menos 1 gol
    - NO: Al menos un equipo no marcará
    """
    SI = "SI"
    NO = "NO"


class ValidacionResultadoEnum(str, Enum):
    """
    Resultado de validación post-partido.
    
    - GANA: El pronóstico fue correcto
    - PIERDE: El pronóstico fue incorrecto
    """
    GANA = "GANA"
    PIERDE = "PIERDE"


# ============================================
# UMBRALES DEL ALGORITMO
# ============================================

class Umbrales:
    """
    Umbrales utilizados en el algoritmo de decisión.
    
    Estos valores fueron calibrados empíricamente en el Excel original.
    Cada umbral tiene un propósito específico en la lógica de decisión.
    
    Atributos:
    ----------
    PROB_LOCAL_MIN : float
        Probabilidad mínima del local para pronosticar victoria local.
        Si la probabilidad está por debajo, no hay suficiente ventaja.
        Valor original: 43%
    
    PROB_LOCAL_MAX : float
        Probabilidad máxima del local para el rango "óptimo".
        Por encima de este valor, el local es "muy favorito".
        Valor original: 69.5%
    
    PROB_EMPATE_MAX : float
        Probabilidad máxima de empate para decidir un ganador claro.
        Si el empate supera este umbral, se considera probable.
        Valor original: 20%
    
    SUMA_PROB_MIN : float
        Suma mínima de probabilidades (local + visita) para "12".
        Indica que el empate es poco probable.
        Valor original: 116%
    
    SUMA_PROB_MAX : float
        Límite superior de la suma de probabilidades.
        Valor original: 123%
    
    PROB_VISITA_MAX : float
        Máximo porcentaje de visita para ciertos cálculos.
        Valor original: 42%
    
    UMBRAL_AMBOS_MARCAN : float
        Umbral para decidir SI/NO en ambos marcan.
        Basado en promedios de goles.
        Valor original: 45%
    
    DIFERENCIA_EMPATE : float
        Diferencia máxima entre probabilidades para considerar empate.
        Si |prob_local - prob_visita| < este valor, equipos parejos.
        Valor original: 10%
    """
    
    # --- Umbrales de Probabilidad Local ---
    PROB_LOCAL_MIN: float = 43.0
    PROB_LOCAL_MAX: float = 69.5
    
    # --- Umbrales de Empate ---
    PROB_EMPATE_MAX: float = 20.0
    DIFERENCIA_EMPATE: float = 10.0
    
    # --- Umbrales de Suma ---
    SUMA_PROB_MIN: float = 116.0
    SUMA_PROB_MAX: float = 123.0
    
    # --- Umbrales de Visita ---
    PROB_VISITA_MAX: float = 42.0
    
    # --- Umbrales de Ambos Marcan ---
    UMBRAL_AMBOS_MARCAN: float = 45.0
    
    # --- Umbrales de Factor de Ajuste ---
    # Rendimiento porcentual para cada factor (1-5)
    FACTOR_5_MIN: float = 80.0  # Factor 5: rendimiento > 80%
    FACTOR_4_MIN: float = 60.0  # Factor 4: rendimiento > 60%
    FACTOR_3_MIN: float = 40.0  # Factor 3: rendimiento > 40%
    FACTOR_2_MIN: float = 20.0  # Factor 2: rendimiento > 20%
    # Factor 1: rendimiento <= 20%
    
    # --- Umbrales de Over/Under ---
    OVER_25_UMBRAL: float = 2.5  # Umbral para Over 2.5 goles
    OVER_15_UMBRAL: float = 1.5  # Umbral para Over 1.5 goles
    OVER_35_UMBRAL: float = 3.5  # Umbral para Over 3.5 goles
    
    # --- Forma Reciente ---
    PARTIDOS_FORMA_RECIENTE: int = 5  # Últimos N partidos para forma
    PESO_FORMA_RECIENTE: float = 0.3  # Peso de forma reciente vs temporada completa
    
    @classmethod
    def to_dict(cls) -> Dict[str, float]:
        """
        Retorna todos los umbrales como diccionario.
        Útil para logging y debugging.
        """
        return {
            'PROB_LOCAL_MIN': cls.PROB_LOCAL_MIN,
            'PROB_LOCAL_MAX': cls.PROB_LOCAL_MAX,
            'PROB_EMPATE_MAX': cls.PROB_EMPATE_MAX,
            'DIFERENCIA_EMPATE': cls.DIFERENCIA_EMPATE,
            'SUMA_PROB_MIN': cls.SUMA_PROB_MIN,
            'SUMA_PROB_MAX': cls.SUMA_PROB_MAX,
            'PROB_VISITA_MAX': cls.PROB_VISITA_MAX,
            'UMBRAL_AMBOS_MARCAN': cls.UMBRAL_AMBOS_MARCAN,
            'FACTOR_5_MIN': cls.FACTOR_5_MIN,
            'FACTOR_4_MIN': cls.FACTOR_4_MIN,
            'FACTOR_3_MIN': cls.FACTOR_3_MIN,
            'FACTOR_2_MIN': cls.FACTOR_2_MIN,
        }


# ============================================
# CONFIGURACIÓN GENERAL
# ============================================

class Config:
    """
    Configuración general del sistema.
    
    Atributos:
    ----------
    VERSION : str
        Versión actual del algoritmo.
    
    PUNTOS_VICTORIA : int
        Puntos otorgados por victoria (estándar: 3)
    
    PUNTOS_EMPATE : int
        Puntos otorgados por empate (estándar: 1)
    
    PUNTOS_DERROTA : int
        Puntos otorgados por derrota (estándar: 0)
    
    PROMEDIOS_POR_DEFECTO : dict
        Valores por defecto cuando no hay datos suficientes.
        Basados en promedios históricos de fútbol.
    """
    
    VERSION: str = "1.0.0"
    
    # Sistema de puntos estándar
    PUNTOS_VICTORIA: int = 3
    PUNTOS_EMPATE: int = 1
    PUNTOS_DERROTA: int = 0
    
    # Mínimo de partidos para cálculos confiables
    MIN_PARTIDOS_CONFIABLE: int = 5
    
    # Promedios por defecto (cuando no hay suficientes datos)
    # Basados en análisis de La Liga 2023:
    # - Local gana: 43.9%
    # - Empate: 28.2%
    # - Visita gana: 27.9%
    PROMEDIOS_POR_DEFECTO: Dict[str, float] = {
        'prob_local': 44.0,
        'prob_empate': 28.0,
        'prob_visita': 28.0,
        'goles_local': 1.48,
        'goles_visita': 1.16,
        'goles_local_1mt': 0.66,
        'goles_visita_1mt': 0.54,
    }
    
    # Colecciones de MongoDB
    COLECCION_PARTIDOS: str = "football_matches"
    COLECCION_ESTADISTICAS: str = "team_statistics"
    COLECCION_PRONOSTICOS: str = "predictions"
    COLECCION_VALIDACIONES: str = "validations"
    
    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """
        Retorna la configuración como diccionario.
        """
        return {
            'version': cls.VERSION,
            'puntos_victoria': cls.PUNTOS_VICTORIA,
            'puntos_empate': cls.PUNTOS_EMPATE,
            'puntos_derrota': cls.PUNTOS_DERROTA,
            'min_partidos_confiable': cls.MIN_PARTIDOS_CONFIABLE,
            'promedios_por_defecto': cls.PROMEDIOS_POR_DEFECTO,
        }


# ============================================
# ALIAS PARA FACILIDAD DE USO
# ============================================

# Acceso directo a umbrales
UMBRALES = Umbrales()
CONFIG = Config()
