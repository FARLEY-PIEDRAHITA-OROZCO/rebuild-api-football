"""
========================================
MÓDULO: prediction_engine
========================================

Motor de Pronósticos Deportivos PLLA 3.0

Este módulo implementa el sistema de pronósticos deportivos
basado en el Excel PLLA 3.0. Incluye:

- Construcción de estadísticas por equipo
- Generación de tablas de clasificación
- Motor de pronósticos con algoritmo de decisión
- Validación de pronósticos contra resultados reales

Uso básico:
-----------
    from prediction_engine import PredictionEngine, StatsBuilder
    
    # Construir estadísticas
    stats_builder = StatsBuilder(db)
    await stats_builder.construir_estadisticas('SPAIN_LA_LIGA')
    
    # Generar pronóstico
    engine = PredictionEngine(db)
    pronostico = await engine.generar_pronostico(
        equipo_local='Barcelona',
        equipo_visitante='Real Madrid',
        liga_id='SPAIN_LA_LIGA'
    )

Módulos:
--------
- models: Modelos de datos (Pydantic)
- config: Configuración y umbrales
- stats_builder: Constructor de estadísticas
- classification: Motor de clasificación
- prediction_engine: Motor de pronósticos
- validation: Validador de pronósticos

Autor: PLLA 3.0 Migration Project
Versión: 1.0.0
Fecha: Diciembre 2024
"""

__version__ = "1.0.0"
__author__ = "PLLA 3.0 Migration Project"

# Importaciones principales
from .models import (
    EstadisticasEquipo,
    Equipo,
    Probabilidades,
    PronosticoTiempo,
    Pronostico,
    Validacion,
    ValidacionTiempo,
    FilaClasificacion,
    TablaClasificacion
)
from .config import (
    Config,
    Umbrales,
    TipoTiempo,
    ResultadoEnum,
    DobleOportunidadEnum,
    AmbosMarcamEnum,
    ValidacionResultadoEnum,
    CONFIG,
    UMBRALES
)
from .stats_builder import StatsBuilder
from .classification import ClassificationEngine
from .prediction_engine import PredictionEngine
from .validation import ValidationEngine
from .backtesting import BacktestingEngine
from .historico_consolidado import HistoricoConsolidado

__all__ = [
    # Modelos
    'EstadisticasEquipo',
    'Equipo',
    'Probabilidades',
    'PronosticoTiempo',
    'Pronostico',
    'Validacion',
    'ValidacionTiempo',
    'FilaClasificacion',
    'TablaClasificacion',
    
    # Configuración
    'Config',
    'Umbrales',
    'TipoTiempo',
    'ResultadoEnum',
    'DobleOportunidadEnum',
    'AmbosMarcamEnum',
    'ValidacionResultadoEnum',
    'CONFIG',
    'UMBRALES',
    
    # Motores
    'StatsBuilder',
    'ClassificationEngine',
    'PredictionEngine',
    'ValidationEngine',
    'BacktestingEngine',
    'HistoricoConsolidado',
]
