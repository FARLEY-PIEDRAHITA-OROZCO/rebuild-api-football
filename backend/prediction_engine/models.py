"""
========================================
MÓDULO: models.py
========================================

Modelos de datos para el Motor de Pronósticos PLLA 3.0.

Este módulo define todas las estructuras de datos utilizadas
en el sistema de pronósticos, usando Pydantic para validación.

Clases Principales:
------------------
- EstadisticasEquipo: Estadísticas acumuladas de un equipo
- Equipo: Equipo con sus estadísticas en los 3 tiempos
- Probabilidades: Porcentajes calculados (L/E/V)
- Pronostico: Resultado del motor de pronósticos
- Validacion: Resultado de validación post-partido

Historial de Cambios:
--------------------
- v1.0.0 (Dic 2024): Versión inicial
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
from uuid import uuid4

from .config import (
    TipoTiempo,
    ResultadoEnum,
    DobleOportunidadEnum,
    AmbosMarcamEnum,
    ValidacionResultadoEnum,
    Config
)


# ============================================
# MODELOS BASE
# ============================================

class BaseModelConfig(BaseModel):
    """
    Configuración base para todos los modelos.
    Permite atributos extra y validación por asignación.
    """
    model_config = ConfigDict(
        extra='allow',
        validate_assignment=True,
        populate_by_name=True
    )


# ============================================
# ESTADÍSTICAS DE EQUIPO
# ============================================

class EstadisticasEquipo(BaseModelConfig):
    """
    Estadísticas acumuladas de un equipo.
    
    Se separan en tres contextos:
    - General: Todos los partidos
    - Local: Solo partidos como local
    - Visitante: Solo partidos como visitante
    
    Atributos Generales:
    -------------------
    partidos_jugados : int
        Total de partidos disputados
    victorias : int
        Total de victorias
    empates : int
        Total de empates
    derrotas : int
        Total de derrotas
    goles_favor : int
        Total de goles marcados
    goles_contra : int
        Total de goles recibidos
    diferencia_goles : int
        Diferencia entre GF y GC
    puntos : int
        Puntos totales (V*3 + E*1)
    
    Atributos como Local:
    --------------------
    pj_local, v_local, e_local, d_local,
    gf_local, gc_local, pts_local
    
    Atributos como Visitante:
    ------------------------
    pj_visita, v_visita, e_visita, d_visita,
    gf_visita, gc_visita, pts_visita
    
    Atributos Derivados:
    -------------------
    rendimiento_general : float
        Porcentaje de puntos obtenidos vs posibles (0-100)
    rendimiento_local : float
        Rendimiento jugando como local
    rendimiento_visita : float
        Rendimiento jugando como visitante
    promedio_gf : float
        Promedio de goles a favor por partido
    promedio_gc : float
        Promedio de goles en contra por partido
    """
    
    # --- Estadísticas Generales ---
    partidos_jugados: int = Field(default=0, ge=0, description="Total partidos jugados")
    victorias: int = Field(default=0, ge=0, description="Total victorias")
    empates: int = Field(default=0, ge=0, description="Total empates")
    derrotas: int = Field(default=0, ge=0, description="Total derrotas")
    goles_favor: int = Field(default=0, ge=0, description="Goles marcados")
    goles_contra: int = Field(default=0, ge=0, description="Goles recibidos")
    diferencia_goles: int = Field(default=0, description="Diferencia de goles")
    puntos: int = Field(default=0, ge=0, description="Puntos totales")
    
    # --- Como Local ---
    pj_local: int = Field(default=0, ge=0, description="Partidos jugados como local")
    v_local: int = Field(default=0, ge=0, description="Victorias como local")
    e_local: int = Field(default=0, ge=0, description="Empates como local")
    d_local: int = Field(default=0, ge=0, description="Derrotas como local")
    gf_local: int = Field(default=0, ge=0, description="Goles favor como local")
    gc_local: int = Field(default=0, ge=0, description="Goles contra como local")
    pts_local: int = Field(default=0, ge=0, description="Puntos como local")
    
    # --- Como Visitante ---
    pj_visita: int = Field(default=0, ge=0, description="Partidos jugados como visitante")
    v_visita: int = Field(default=0, ge=0, description="Victorias como visitante")
    e_visita: int = Field(default=0, ge=0, description="Empates como visitante")
    d_visita: int = Field(default=0, ge=0, description="Derrotas como visitante")
    gf_visita: int = Field(default=0, ge=0, description="Goles favor como visitante")
    gc_visita: int = Field(default=0, ge=0, description="Goles contra como visitante")
    pts_visita: int = Field(default=0, ge=0, description="Puntos como visitante")
    
    # --- Derivados (calculados) ---
    rendimiento_general: float = Field(default=0.0, ge=0, le=100, description="Rendimiento general %")
    rendimiento_local: float = Field(default=0.0, ge=0, le=100, description="Rendimiento local %")
    rendimiento_visita: float = Field(default=0.0, ge=0, le=100, description="Rendimiento visitante %")
    promedio_gf: float = Field(default=0.0, ge=0, description="Promedio goles favor")
    promedio_gc: float = Field(default=0.0, ge=0, description="Promedio goles contra")
    
    def calcular_derivados(self) -> None:
        """
        Calcula los campos derivados basados en las estadísticas base.
        
        Fórmulas:
        - rendimiento = (puntos / puntos_posibles) * 100
        - puntos_posibles = partidos_jugados * 3
        - promedio = total / partidos_jugados
        """
        # Rendimiento general
        if self.partidos_jugados > 0:
            puntos_posibles = self.partidos_jugados * Config.PUNTOS_VICTORIA
            self.rendimiento_general = round((self.puntos / puntos_posibles) * 100, 2)
            self.promedio_gf = round(self.goles_favor / self.partidos_jugados, 2)
            self.promedio_gc = round(self.goles_contra / self.partidos_jugados, 2)
        
        # Rendimiento local
        if self.pj_local > 0:
            puntos_posibles_local = self.pj_local * Config.PUNTOS_VICTORIA
            self.rendimiento_local = round((self.pts_local / puntos_posibles_local) * 100, 2)
        
        # Rendimiento visitante
        if self.pj_visita > 0:
            puntos_posibles_visita = self.pj_visita * Config.PUNTOS_VICTORIA
            self.rendimiento_visita = round((self.pts_visita / puntos_posibles_visita) * 100, 2)


class Equipo(BaseModelConfig):
    """
    Equipo de fútbol con sus estadísticas.
    
    Incluye estadísticas separadas para:
    - Tiempo Completo (90 min)
    - Primer Tiempo (1MT)
    - Segundo Tiempo (2MT)
    
    Atributos:
    ----------
    id : str
        Identificador único
    nombre : str
        Nombre del equipo
    liga_id : str
        Identificador de la liga
    temporada : int
        Año de la temporada
    stats_completo : EstadisticasEquipo
        Estadísticas de tiempo completo
    stats_primer_tiempo : EstadisticasEquipo
        Estadísticas de primer tiempo
    stats_segundo_tiempo : EstadisticasEquipo
        Estadísticas de segundo tiempo
    """
    
    id: str = Field(default_factory=lambda: str(uuid4()), description="ID único")
    nombre: str = Field(..., min_length=1, description="Nombre del equipo")
    liga_id: str = Field(..., description="ID de la liga")
    temporada: int = Field(..., ge=1900, le=2100, description="Año de temporada")
    season_id: Optional[str] = Field(
        default=None, 
        description="ID de temporada estructurado (ej: SPAIN_LA_LIGA_2023-24)"
    )
    
    # Estadísticas por tiempo
    stats_completo: EstadisticasEquipo = Field(
        default_factory=EstadisticasEquipo,
        description="Stats tiempo completo (90 min)"
    )
    stats_primer_tiempo: EstadisticasEquipo = Field(
        default_factory=EstadisticasEquipo,
        description="Stats primer tiempo (1MT)"
    )
    stats_segundo_tiempo: EstadisticasEquipo = Field(
        default_factory=EstadisticasEquipo,
        description="Stats segundo tiempo (2MT)"
    )
    
    # Metadata
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Fecha de creación"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Fecha de actualización"
    )
    
    def obtener_stats(self, tipo_tiempo: TipoTiempo) -> EstadisticasEquipo:
        """
        Obtiene las estadísticas según el tipo de tiempo.
        
        Parámetros:
        -----------
        tipo_tiempo : TipoTiempo
            COMPLETO, PRIMER_TIEMPO o SEGUNDO_TIEMPO
        
        Retorna:
        --------
        EstadisticasEquipo
            Estadísticas correspondientes
        """
        if tipo_tiempo == TipoTiempo.COMPLETO:
            return self.stats_completo
        elif tipo_tiempo == TipoTiempo.PRIMER_TIEMPO:
            return self.stats_primer_tiempo
        else:
            return self.stats_segundo_tiempo


# ============================================
# PROBABILIDADES Y PRONÓSTICOS
# ============================================

class Probabilidades(BaseModelConfig):
    """
    Probabilidades calculadas para un partido.
    
    La suma de los tres porcentajes debe ser cercana a 100%.
    Pequeñas variaciones pueden ocurrir por redondeo.
    
    Atributos:
    ----------
    porcentaje_local : float
        Probabilidad de victoria local (0-100)
    porcentaje_empate : float
        Probabilidad de empate (0-100)
    porcentaje_visita : float
        Probabilidad de victoria visitante (0-100)
    """
    
    porcentaje_local: float = Field(
        default=0.0, ge=0, le=100,
        description="% probabilidad victoria local"
    )
    porcentaje_empate: float = Field(
        default=0.0, ge=0, le=100,
        description="% probabilidad empate"
    )
    porcentaje_visita: float = Field(
        default=0.0, ge=0, le=100,
        description="% probabilidad victoria visita"
    )
    
    def suma(self) -> float:
        """Retorna la suma de probabilidades."""
        return self.porcentaje_local + self.porcentaje_empate + self.porcentaje_visita
    
    def to_dict(self) -> Dict[str, float]:
        """Convierte a diccionario simple."""
        return {
            'local': self.porcentaje_local,
            'empate': self.porcentaje_empate,
            'visita': self.porcentaje_visita
        }


class PronosticoTiempo(BaseModelConfig):
    """
    Pronóstico para un tiempo específico (TC, 1MT o 2MT).
    
    Atributos:
    ----------
    pronostico : str
        Resultado pronosticado ("L", "E", "V")
    doble_oportunidad : str
        Apuesta doble ("1X", "X2", "12")
    ambos_marcan : str
        Si ambos marcarán ("SI", "NO")
    probabilidades : Probabilidades
        Porcentajes calculados
    confianza : float
        Nivel de confianza del pronóstico (0-100)
    factor_local : int
        Factor de ajuste del local (1-5)
    factor_visita : int
        Factor de ajuste del visitante (1-5)
    over_under : dict
        Predicciones de Over/Under goles
    goles_esperados : dict
        Goles esperados por equipo
    """
    
    pronostico: str = Field(..., description="Resultado: L/E/V")
    doble_oportunidad: str = Field(..., description="Doble op: 1X/X2/12")
    ambos_marcan: str = Field(..., description="Ambos marcan: SI/NO")
    probabilidades: Probabilidades = Field(..., description="Probabilidades")
    confianza: float = Field(default=0.0, ge=0, le=100, description="% confianza")
    factor_local: int = Field(default=3, ge=1, le=5, description="Factor local")
    factor_visita: int = Field(default=3, ge=1, le=5, description="Factor visita")
    
    # Nuevos campos para Over/Under
    over_under: Dict[str, Any] = Field(
        default_factory=lambda: {
            "over_15": {"prediccion": "OVER", "probabilidad": 50.0},
            "over_25": {"prediccion": "UNDER", "probabilidad": 50.0},
            "over_35": {"prediccion": "UNDER", "probabilidad": 50.0}
        },
        description="Predicciones Over/Under"
    )
    goles_esperados: Dict[str, float] = Field(
        default_factory=lambda: {"local": 0.0, "visitante": 0.0, "total": 0.0},
        description="Goles esperados"
    )


class Pronostico(BaseModelConfig):
    """
    Pronóstico completo para un partido.
    
    Incluye pronósticos para los tres tiempos.
    
    Atributos:
    ----------
    id : str
        Identificador único del pronóstico
    partido_id : str
        ID del partido (si aplica)
    equipo_local : str
        Nombre del equipo local
    equipo_visitante : str
        Nombre del equipo visitante
    liga_id : str
        ID de la liga
    season_id : str
        ID de temporada estructurado
    
    tiempo_completo : PronosticoTiempo
        Pronóstico para 90 minutos
    primer_tiempo : PronosticoTiempo
        Pronóstico para 1er tiempo
    segundo_tiempo : PronosticoTiempo
        Pronóstico para 2do tiempo
    
    forma_reciente : dict
        Forma de los últimos 5 partidos de cada equipo
    
    version_algoritmo : str
        Versión del algoritmo usado
    fecha_generacion : datetime
        Fecha/hora de generación
    """
    
    id: str = Field(default_factory=lambda: str(uuid4()), description="ID único")
    partido_id: Optional[str] = Field(default=None, description="ID del partido")
    equipo_local: str = Field(..., description="Equipo local")
    equipo_visitante: str = Field(..., description="Equipo visitante")
    liga_id: str = Field(..., description="ID de la liga")
    season_id: Optional[str] = Field(default=None, description="ID de temporada estructurado")
    
    # Pronósticos por tiempo
    tiempo_completo: PronosticoTiempo = Field(..., description="Pronóstico TC")
    primer_tiempo: PronosticoTiempo = Field(..., description="Pronóstico 1MT")
    segundo_tiempo: PronosticoTiempo = Field(..., description="Pronóstico 2MT")
    
    # Forma reciente de los equipos
    forma_reciente: Dict[str, Any] = Field(
        default_factory=lambda: {
            "local": {
                "ultimos_5": [],
                "rendimiento": 0.0,
                "goles_favor_avg": 0.0,
                "goles_contra_avg": 0.0,
                "racha": ""
            },
            "visitante": {
                "ultimos_5": [],
                "rendimiento": 0.0,
                "goles_favor_avg": 0.0,
                "goles_contra_avg": 0.0,
                "racha": ""
            }
        },
        description="Forma reciente de los equipos"
    )
    
    # Histórico H2H (enfrentamientos directos)
    h2h: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Historial de enfrentamientos directos"
    )
    
    # Temporadas analizadas
    temporadas_analizadas: int = Field(
        default=1,
        description="Número de temporadas usadas para el análisis"
    )
    
    # Metadata
    version_algoritmo: str = Field(default=Config.VERSION, description="Versión")
    fecha_generacion: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Fecha generación"
    )
    
    def to_response_dict(self) -> Dict[str, Any]:
        """
        Convierte a diccionario para respuesta API.
        Formato simplificado y legible.
        """
        return {
            'id': self.id,
            'equipo_local': self.equipo_local,
            'equipo_visitante': self.equipo_visitante,
            'liga_id': self.liga_id,
            'season_id': self.season_id,
            'tiempo_completo': {
                'pronostico': self.tiempo_completo.pronostico,
                'doble_oportunidad': self.tiempo_completo.doble_oportunidad,
                'ambos_marcan': self.tiempo_completo.ambos_marcan,
                'probabilidades': self.tiempo_completo.probabilidades.to_dict(),
                'confianza': self.tiempo_completo.confianza,
                'over_under': self.tiempo_completo.over_under,
                'goles_esperados': self.tiempo_completo.goles_esperados
            },
            'primer_tiempo': {
                'pronostico': self.primer_tiempo.pronostico,
                'doble_oportunidad': self.primer_tiempo.doble_oportunidad,
                'ambos_marcan': self.primer_tiempo.ambos_marcan,
                'probabilidades': self.primer_tiempo.probabilidades.to_dict(),
                'confianza': self.primer_tiempo.confianza,
                'over_under': self.primer_tiempo.over_under,
                'goles_esperados': self.primer_tiempo.goles_esperados
            },
            'segundo_tiempo': {
                'pronostico': self.segundo_tiempo.pronostico,
                'doble_oportunidad': self.segundo_tiempo.doble_oportunidad,
                'ambos_marcan': self.segundo_tiempo.ambos_marcan,
                'probabilidades': self.segundo_tiempo.probabilidades.to_dict(),
                'confianza': self.segundo_tiempo.confianza,
                'over_under': self.segundo_tiempo.over_under,
                'goles_esperados': self.segundo_tiempo.goles_esperados
            },
            'forma_reciente': self.forma_reciente,
            'h2h': self.h2h,
            'temporadas_analizadas': self.temporadas_analizadas,
            'version_algoritmo': self.version_algoritmo,
            'fecha_generacion': self.fecha_generacion.isoformat()
        }


# ============================================
# VALIDACIÓN
# ============================================

class ValidacionTiempo(BaseModelConfig):
    """
    Resultado de validación para un tiempo específico.
    
    Atributos:
    ----------
    resultado_doble_oportunidad : str
        "GANA" si el pronóstico de doble oportunidad acertó, "PIERDE" si no
    resultado_ambos_marcan : str
        "GANA" si acertó ambos marcan, "PIERDE" si no
    pronostico_original : str
        El pronóstico que se hizo (L/E/V)
    resultado_real : str
        El resultado real del partido (L/E/V)
    """
    
    resultado_doble_oportunidad: str = Field(..., description="GANA/PIERDE")
    resultado_ambos_marcan: str = Field(..., description="GANA/PIERDE")
    pronostico_original: str = Field(..., description="Pronóstico hecho")
    resultado_real: str = Field(..., description="Resultado real")
    acierto_principal: bool = Field(..., description="Si acertó L/E/V")


class Validacion(BaseModelConfig):
    """
    Validación completa de un pronóstico.
    
    Se genera después de que el partido se ha jugado.
    Compara el pronóstico con el resultado real.
    
    Atributos:
    ----------
    id : str
        ID único de la validación
    pronostico_id : str
        ID del pronóstico validado
    partido_id : str
        ID del partido
    
    gol_local_tc : int
        Goles del local tiempo completo
    gol_visita_tc : int
        Goles de visita tiempo completo
    gol_local_1mt : int
        Goles del local primer tiempo
    gol_visita_1mt : int
        Goles de visita primer tiempo
    
    validacion_tc : ValidacionTiempo
        Validación tiempo completo
    validacion_1mt : ValidacionTiempo
        Validación primer tiempo
    validacion_2mt : ValidacionTiempo
        Validación segundo tiempo
    """
    
    id: str = Field(default_factory=lambda: str(uuid4()), description="ID único")
    pronostico_id: str = Field(..., description="ID del pronóstico")
    partido_id: Optional[str] = Field(default=None, description="ID del partido")
    
    # Resultados reales
    gol_local_tc: int = Field(..., ge=0, description="Goles local TC")
    gol_visita_tc: int = Field(..., ge=0, description="Goles visita TC")
    gol_local_1mt: int = Field(default=0, ge=0, description="Goles local 1MT")
    gol_visita_1mt: int = Field(default=0, ge=0, description="Goles visita 1MT")
    
    # Validaciones por tiempo
    validacion_tc: ValidacionTiempo = Field(..., description="Validación TC")
    validacion_1mt: Optional[ValidacionTiempo] = Field(default=None, description="Validación 1MT")
    validacion_2mt: Optional[ValidacionTiempo] = Field(default=None, description="Validación 2MT")
    
    # Metadata
    fecha_validacion: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Fecha de validación"
    )


# ============================================
# MODELOS DE CLASIFICACIÓN
# ============================================

class FilaClasificacion(BaseModelConfig):
    """
    Una fila de la tabla de clasificación.
    
    Atributos:
    ----------
    posicion : int
        Posición en la tabla (1 = primero)
    equipo : str
        Nombre del equipo
    pj : int
        Partidos jugados
    v, e, d : int
        Victorias, empates, derrotas
    gf, gc, dif : int
        Goles favor, contra, diferencia
    pts : int
        Puntos totales
    
    También incluye stats de local y visitante.
    """
    
    posicion: int = Field(default=0, ge=0, description="Posición")
    equipo: str = Field(..., description="Nombre equipo")
    
    # Generales
    pj: int = Field(default=0, ge=0)
    v: int = Field(default=0, ge=0)
    e: int = Field(default=0, ge=0)
    d: int = Field(default=0, ge=0)
    gf: int = Field(default=0, ge=0)
    gc: int = Field(default=0, ge=0)
    dif: int = Field(default=0)
    pts: int = Field(default=0, ge=0)
    
    # Como local
    pj_l: int = Field(default=0, ge=0)
    v_l: int = Field(default=0, ge=0)
    e_l: int = Field(default=0, ge=0)
    d_l: int = Field(default=0, ge=0)
    gf_l: int = Field(default=0, ge=0)
    gc_l: int = Field(default=0, ge=0)
    pts_l: int = Field(default=0, ge=0)
    
    # Como visitante
    pj_v: int = Field(default=0, ge=0)
    v_v: int = Field(default=0, ge=0)
    e_v: int = Field(default=0, ge=0)
    d_v: int = Field(default=0, ge=0)
    gf_v: int = Field(default=0, ge=0)
    gc_v: int = Field(default=0, ge=0)
    pts_v: int = Field(default=0, ge=0)
    
    # Rendimientos
    rendimiento: float = Field(default=0.0, ge=0, le=100)
    rendimiento_l: float = Field(default=0.0, ge=0, le=100)
    rendimiento_v: float = Field(default=0.0, ge=0, le=100)


class TablaClasificacion(BaseModelConfig):
    """
    Tabla de clasificación completa.
    
    Atributos:
    ----------
    liga_id : str
        ID de la liga
    temporada : int
        Año de la temporada
    tipo_tiempo : str
        Tipo de tiempo (completo, primer_tiempo, segundo_tiempo)
    filas : List[FilaClasificacion]
        Lista de equipos ordenados por posición
    fecha_actualizacion : datetime
        Última actualización
    """
    
    liga_id: str = Field(..., description="ID de la liga")
    temporada: int = Field(..., description="Año de temporada")
    tipo_tiempo: str = Field(..., description="Tipo de tiempo")
    filas: List[FilaClasificacion] = Field(default_factory=list, description="Filas")
    fecha_actualizacion: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
