"""
========================================
MÓDULO: validation.py
========================================

Validador de Pronósticos - Sistema GANA/PIERDE.

Este módulo compara los pronósticos generados con los
resultados reales de los partidos, determinando la
efectividad del sistema.

Funcionalidades:
---------------
- Validar pronósticos individuales
- Calcular estadísticas de efectividad
- Generar reportes de rendimiento

Clases:
-------
- ValidationEngine: Motor de validación

Historial de Cambios:
--------------------
- v1.0.0 (Dic 2024): Versión inicial
"""

from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone
import logging

from .models import (
    Pronostico,
    Validacion,
    ValidacionTiempo
)
from .config import (
    Config,
    ResultadoEnum,
    DobleOportunidadEnum,
    ValidacionResultadoEnum
)

logger = logging.getLogger(__name__)


class ValidationEngine:
    """
    Motor de Validación de Pronósticos.
    
    Compara pronósticos con resultados reales y calcula
    métricas de efectividad del sistema.
    
    Atributos:
    ----------
    db : AsyncIOMotorDatabase
        Conexión a MongoDB
    
    Métodos Públicos:
    ----------------
    validar_pronostico(pronostico_id, goles)
        Valida un pronóstico contra el resultado real
    
    calcular_efectividad(liga_id, periodo)
        Calcula estadísticas de efectividad
    
    Ejemplo de Uso:
    ---------------
    ```python
    validator = ValidationEngine(db)
    
    # Validar un pronóstico
    resultado = await validator.validar_pronostico(
        pronostico_id='abc123',
        gol_local_tc=2,
        gol_visita_tc=1,
        gol_local_1mt=1,
        gol_visita_1mt=0
    )
    
    print(resultado.validacion_tc.resultado_doble_oportunidad)  # "GANA"
    ```
    """
    
    def __init__(self, db):
        """
        Inicializa el validador.
        
        Parámetros:
        -----------
        db : AsyncIOMotorDatabase
            Conexión a MongoDB
        """
        self.db = db
        logger.info("ValidationEngine inicializado")
    
    async def validar_pronostico(
        self,
        pronostico_id: str,
        gol_local_tc: int,
        gol_visita_tc: int,
        gol_local_1mt: int = 0,
        gol_visita_1mt: int = 0
    ) -> Validacion:
        """
        Valida un pronóstico contra el resultado real.
        
        Parámetros:
        -----------
        pronostico_id : str
            ID del pronóstico a validar
        gol_local_tc : int
            Goles del local tiempo completo
        gol_visita_tc : int
            Goles de la visita tiempo completo
        gol_local_1mt : int
            Goles del local primer tiempo
        gol_visita_1mt : int
            Goles de la visita primer tiempo
        
        Retorna:
        --------
        Validacion
            Resultado de la validación
        
        Raises:
        -------
        ValueError
            Si no se encuentra el pronóstico
        
        Ejemplo:
        --------
        ```python
        validacion = await validator.validar_pronostico(
            pronostico_id='abc123',
            gol_local_tc=2,
            gol_visita_tc=1
        )
        
        if validacion.validacion_tc.resultado_doble_oportunidad == "GANA":
            print("¡Pronóstico acertado!")
        ```
        """
        logger.info(f"Validando pronóstico {pronostico_id}")
        
        # Obtener pronóstico
        pronostico_doc = await self.db[Config.COLECCION_PRONOSTICOS].find_one(
            {"id": pronostico_id}
        )
        
        if not pronostico_doc:
            raise ValueError(f"Pronóstico no encontrado: {pronostico_id}")
        
        pronostico_doc.pop('_id', None)
        pronostico = Pronostico(**pronostico_doc)
        
        # Calcular goles 2MT
        gol_local_2mt = gol_local_tc - gol_local_1mt
        gol_visita_2mt = gol_visita_tc - gol_visita_1mt
        
        # Determinar resultados reales
        resultado_tc = self._determinar_resultado(gol_local_tc, gol_visita_tc)
        resultado_1mt = self._determinar_resultado(gol_local_1mt, gol_visita_1mt)
        resultado_2mt = self._determinar_resultado(gol_local_2mt, gol_visita_2mt)
        
        # Validar tiempo completo
        validacion_tc = self._validar_tiempo(
            pronostico.tiempo_completo.pronostico,
            pronostico.tiempo_completo.doble_oportunidad,
            pronostico.tiempo_completo.ambos_marcan,
            resultado_tc,
            gol_local_tc,
            gol_visita_tc
        )
        
        # Validar primer tiempo
        validacion_1mt = self._validar_tiempo(
            pronostico.primer_tiempo.pronostico,
            pronostico.primer_tiempo.doble_oportunidad,
            pronostico.primer_tiempo.ambos_marcan,
            resultado_1mt,
            gol_local_1mt,
            gol_visita_1mt
        )
        
        # Validar segundo tiempo
        validacion_2mt = self._validar_tiempo(
            pronostico.segundo_tiempo.pronostico,
            pronostico.segundo_tiempo.doble_oportunidad,
            pronostico.segundo_tiempo.ambos_marcan,
            resultado_2mt,
            gol_local_2mt,
            gol_visita_2mt
        )
        
        # Crear validación
        validacion = Validacion(
            pronostico_id=pronostico_id,
            partido_id=pronostico.partido_id,
            gol_local_tc=gol_local_tc,
            gol_visita_tc=gol_visita_tc,
            gol_local_1mt=gol_local_1mt,
            gol_visita_1mt=gol_visita_1mt,
            validacion_tc=validacion_tc,
            validacion_1mt=validacion_1mt,
            validacion_2mt=validacion_2mt
        )
        
        # Guardar validación
        await self._guardar_validacion(validacion)
        
        logger.info(f"Validación completada - TC: {validacion_tc.resultado_doble_oportunidad}")
        
        return validacion
    
    def _determinar_resultado(self, gol_local: int, gol_visita: int) -> str:
        """
        Determina el resultado de un partido.
        
        Parámetros:
        -----------
        gol_local : int
            Goles del local
        gol_visita : int
            Goles de la visita
        
        Retorna:
        --------
        str
            "L", "E" o "V"
        """
        if gol_local > gol_visita:
            return ResultadoEnum.LOCAL.value
        elif gol_local == gol_visita:
            return ResultadoEnum.EMPATE.value
        else:
            return ResultadoEnum.VISITA.value
    
    def _validar_tiempo(
        self,
        pronostico: str,
        doble_oportunidad: str,
        ambos_marcan: str,
        resultado_real: str,
        gol_local: int,
        gol_visita: int
    ) -> ValidacionTiempo:
        """
        Valida el pronóstico de un tiempo específico.
        
        Parámetros:
        -----------
        pronostico : str
            Pronóstico hecho (L/E/V)
        doble_oportunidad : str
            Doble oportunidad pronosticada (1X/X2/12)
        ambos_marcan : str
            Ambos marcan pronosticado (SI/NO)
        resultado_real : str
            Resultado real del partido (L/E/V)
        gol_local : int
            Goles del local
        gol_visita : int
            Goles de la visita
        
        Retorna:
        --------
        ValidacionTiempo
            Resultado de la validación
        """
        # Validar pronóstico principal
        acierto_principal = (pronostico == resultado_real)
        
        # Validar doble oportunidad
        resultado_doble = self._validar_doble_oportunidad(
            doble_oportunidad, resultado_real
        )
        
        # Validar ambos marcan
        ambos_marcaron = (gol_local > 0 and gol_visita > 0)
        if (ambos_marcan == "SI" and ambos_marcaron) or \
           (ambos_marcan == "NO" and not ambos_marcaron):
            resultado_ambos = ValidacionResultadoEnum.GANA.value
        else:
            resultado_ambos = ValidacionResultadoEnum.PIERDE.value
        
        return ValidacionTiempo(
            resultado_doble_oportunidad=resultado_doble,
            resultado_ambos_marcan=resultado_ambos,
            pronostico_original=pronostico,
            resultado_real=resultado_real,
            acierto_principal=acierto_principal
        )
    
    def _validar_doble_oportunidad(
        self,
        doble_oportunidad: str,
        resultado_real: str
    ) -> str:
        """
        Valida si la doble oportunidad acertó.
        
        Lógica:
        - 1X: Acierta si resultado es L o E
        - X2: Acierta si resultado es E o V
        - 12: Acierta si resultado es L o V
        
        Parámetros:
        -----------
        doble_oportunidad : str
            Apuesta realizada
        resultado_real : str
            Resultado del partido
        
        Retorna:
        --------
        str
            "GANA" o "PIERDE"
        """
        # Definir qué resultados cubre cada doble oportunidad
        cobertura = {
            DobleOportunidadEnum.LOCAL_EMPATE.value: [
                ResultadoEnum.LOCAL.value, 
                ResultadoEnum.EMPATE.value
            ],  # 1X
            DobleOportunidadEnum.EMPATE_VISITA.value: [
                ResultadoEnum.EMPATE.value, 
                ResultadoEnum.VISITA.value
            ],  # X2
            DobleOportunidadEnum.LOCAL_VISITA.value: [
                ResultadoEnum.LOCAL.value, 
                ResultadoEnum.VISITA.value
            ]   # 12
        }
        
        if resultado_real in cobertura.get(doble_oportunidad, []):
            return ValidacionResultadoEnum.GANA.value
        else:
            return ValidacionResultadoEnum.PIERDE.value
    
    async def _guardar_validacion(self, validacion: Validacion) -> None:
        """
        Guarda la validación en la base de datos.
        """
        collection = self.db[Config.COLECCION_VALIDACIONES]
        validacion_dict = validacion.model_dump()
        await collection.insert_one(validacion_dict)
        logger.debug(f"Validación guardada: {validacion.id}")
    
    async def calcular_efectividad(
        self,
        liga_id: Optional[str] = None,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Calcula estadísticas de efectividad del sistema.
        
        Parámetros:
        -----------
        liga_id : str, optional
            Filtrar por liga
        fecha_inicio : datetime, optional
            Fecha inicio del periodo
        fecha_fin : datetime, optional
            Fecha fin del periodo
        
        Retorna:
        --------
        Dict
            Estadísticas de efectividad
        
        Ejemplo:
        --------
        ```python
        efectividad = await validator.calcular_efectividad('SPAIN_LA_LIGA')
        print(f"Efectividad doble oportunidad: {efectividad['doble_oportunidad']['accuracy']}%")
        ```
        """
        logger.info("Calculando efectividad del sistema")
        
        # Construir query
        query = {}
        if fecha_inicio:
            query['fecha_validacion'] = {'$gte': fecha_inicio}
        if fecha_fin:
            if 'fecha_validacion' in query:
                query['fecha_validacion']['$lte'] = fecha_fin
            else:
                query['fecha_validacion'] = {'$lte': fecha_fin}
        
        # Obtener validaciones
        validaciones = await self.db[Config.COLECCION_VALIDACIONES].find(
            query
        ).to_list(None)
        
        if not validaciones:
            return {
                'total_validaciones': 0,
                'mensaje': 'No hay validaciones para el periodo especificado'
            }
        
        # Contadores
        total = len(validaciones)
        
        # Tiempo Completo
        tc_doble_gana = 0
        tc_ambos_gana = 0
        tc_principal_acierta = 0
        
        # Primer Tiempo
        mt1_doble_gana = 0
        mt1_ambos_gana = 0
        
        # Segundo Tiempo
        mt2_doble_gana = 0
        mt2_ambos_gana = 0
        
        for v in validaciones:
            # Tiempo Completo
            if 'validacion_tc' in v and v['validacion_tc']:
                if v['validacion_tc'].get('resultado_doble_oportunidad') == 'GANA':
                    tc_doble_gana += 1
                if v['validacion_tc'].get('resultado_ambos_marcan') == 'GANA':
                    tc_ambos_gana += 1
                if v['validacion_tc'].get('acierto_principal'):
                    tc_principal_acierta += 1
            
            # Primer Tiempo
            if 'validacion_1mt' in v and v['validacion_1mt']:
                if v['validacion_1mt'].get('resultado_doble_oportunidad') == 'GANA':
                    mt1_doble_gana += 1
                if v['validacion_1mt'].get('resultado_ambos_marcan') == 'GANA':
                    mt1_ambos_gana += 1
            
            # Segundo Tiempo
            if 'validacion_2mt' in v and v['validacion_2mt']:
                if v['validacion_2mt'].get('resultado_doble_oportunidad') == 'GANA':
                    mt2_doble_gana += 1
                if v['validacion_2mt'].get('resultado_ambos_marcan') == 'GANA':
                    mt2_ambos_gana += 1
        
        # Calcular porcentajes
        return {
            'total_validaciones': total,
            'tiempo_completo': {
                'doble_oportunidad': {
                    'aciertos': tc_doble_gana,
                    'accuracy': round(tc_doble_gana / total * 100, 2) if total > 0 else 0
                },
                'ambos_marcan': {
                    'aciertos': tc_ambos_gana,
                    'accuracy': round(tc_ambos_gana / total * 100, 2) if total > 0 else 0
                },
                'principal': {
                    'aciertos': tc_principal_acierta,
                    'accuracy': round(tc_principal_acierta / total * 100, 2) if total > 0 else 0
                }
            },
            'primer_tiempo': {
                'doble_oportunidad': {
                    'aciertos': mt1_doble_gana,
                    'accuracy': round(mt1_doble_gana / total * 100, 2) if total > 0 else 0
                },
                'ambos_marcan': {
                    'aciertos': mt1_ambos_gana,
                    'accuracy': round(mt1_ambos_gana / total * 100, 2) if total > 0 else 0
                }
            },
            'segundo_tiempo': {
                'doble_oportunidad': {
                    'aciertos': mt2_doble_gana,
                    'accuracy': round(mt2_doble_gana / total * 100, 2) if total > 0 else 0
                },
                'ambos_marcan': {
                    'aciertos': mt2_ambos_gana,
                    'accuracy': round(mt2_ambos_gana / total * 100, 2) if total > 0 else 0
                }
            },
            'version_algoritmo': Config.VERSION
        }
