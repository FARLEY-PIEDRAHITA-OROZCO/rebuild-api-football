#!/usr/bin/env python3
"""Script para exportar datos de la base de datos a diferentes formatos."""

import csv
import json
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from pathlib import Path
import argparse

# Cargar variables de entorno
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

MONGO_URL = os.getenv('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.getenv('DB_NAME', 'test_database')


def export_to_csv(output_file: str, liga_id: str = None, limit: int = 0):
    """Exporta datos a CSV.
    
    Args:
        output_file: Archivo de salida
        liga_id: Filtrar por liga específica (opcional)
        limit: Límite de registros (0 = todos)
    """
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    collection = db['football_matches']
    
    # Construir query
    query = {}
    if liga_id:
        query['liga_id'] = liga_id
    
    # Obtener datos
    cursor = collection.find(query, {'_id': 0})
    if limit > 0:
        cursor = cursor.limit(limit)
    
    partidos = list(cursor)
    
    if not partidos:
        print("No hay datos para exportar")
        return
    
    # Escribir CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=partidos[0].keys())
        writer.writeheader()
        writer.writerows(partidos)
    
    print(f"✓ Exportados {len(partidos)} partidos a {output_file}")
    client.close()


def export_to_json(output_file: str, liga_id: str = None, limit: int = 0):
    """Exporta datos a JSON.
    
    Args:
        output_file: Archivo de salida
        liga_id: Filtrar por liga específica (opcional)
        limit: Límite de registros (0 = todos)
    """
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    collection = db['football_matches']
    
    # Construir query
    query = {}
    if liga_id:
        query['liga_id'] = liga_id
    
    # Obtener datos
    cursor = collection.find(query, {'_id': 0})
    if limit > 0:
        cursor = cursor.limit(limit)
    
    partidos = list(cursor)
    
    if not partidos:
        print("No hay datos para exportar")
        return
    
    # Escribir JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(partidos, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Exportados {len(partidos)} partidos a {output_file}")
    client.close()


def export_table_format(output_file: str, liga_id: str = None, limit: int = 10):
    """Exporta datos en formato de tabla legible.
    
    Args:
        output_file: Archivo de salida
        liga_id: Filtrar por liga específica (opcional)
        limit: Límite de registros (0 = todos)
    """
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    collection = db['football_matches']
    
    # Construir query
    query = {}
    if liga_id:
        query['liga_id'] = liga_id
    
    # Obtener datos
    cursor = collection.find(query, {'_id': 0})
    if limit > 0:
        cursor = cursor.limit(limit)
    
    partidos = list(cursor)
    
    if not partidos:
        print("No hay datos para exportar")
        return
    
    # Escribir en formato tabla
    with open(output_file, 'w', encoding='utf-8') as f:
        # Encabezado
        f.write("="*200 + "\n")
        f.write("PARTIDOS DE FÚTBOL - FORMATO TABLA\n")
        f.write("="*200 + "\n\n")
        
        # Cabecera de tabla
        f.write("-"*200 + "\n")
        f.write(
            f"{'LIGA':<30} | "
            f"{'POS.LOCAL':>9} | "
            f"{'POS.VISITA':>10} | "
            f"{'FECHA':>10} | "
            f"{'HORA':>5} | "
            f"{'LOCAL':<25} | "
            f"{'GOL 1MT':>7} | "
            f"{'GOL GEN':>7} | "
            f"{'VISITANTE':<25} | "
            f"{'GOL 1MT':>7} | "
            f"{'GOL GEN':>7}\n"
        )
        f.write("-"*200 + "\n")
        
        # Datos
        for partido in partidos:
            f.write(
                f"{partido['liga_id']:<30} | "
                f"{partido['pos_clasif_local']:>9} | "
                f"{partido['pos_clasif_visita']:>10} | "
                f"{partido['fecha']:>10} | "
                f"{partido['hora']:>5} | "
                f"{partido['equipo_local']:<25} | "
                f"{partido['goles_local_1MT']:>7} | "
                f"{partido['goles_local_TR']:>7} | "
                f"{partido['equipo_visitante']:<25} | "
                f"{partido['goles_visitante_1MT']:>7} | "
                f"{partido['goles_visitante_TR']:>7}\n"
            )
        
        f.write("-"*200 + "\n")
        f.write(f"\nTotal de partidos: {len(partidos)}\n")
    
    print(f"✓ Exportados {len(partidos)} partidos a {output_file}")
    client.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Exporta datos de partidos a diferentes formatos'
    )
    
    parser.add_argument(
        '--format',
        type=str,
        choices=['csv', 'json', 'table'],
        required=True,
        help='Formato de exportación'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        required=True,
        help='Archivo de salida'
    )
    
    parser.add_argument(
        '--liga',
        type=str,
        help='Filtrar por liga_id (ej: SPAIN_LA_LIGA)'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=0,
        help='Límite de registros (0 = todos)'
    )
    
    args = parser.parse_args()
    
    if args.format == 'csv':
        export_to_csv(args.output, args.liga, args.limit)
    elif args.format == 'json':
        export_to_json(args.output, args.liga, args.limit)
    elif args.format == 'table':
        export_table_format(args.output, args.liga, args.limit)
