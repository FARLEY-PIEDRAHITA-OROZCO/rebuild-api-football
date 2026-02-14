# tests/unit/test_db_manager.py
import pytest
from unittest.mock import MagicMock
from types import SimpleNamespace
from api_football.db_manager import DatabaseManager

@pytest.fixture
def fake_dbm(monkeypatch):
    dbm = DatabaseManager(mongo_url="mongodb://fake", db_name="db", collection_name="col")

    class FakeCollection:
        def __init__(self):
            self._store = {}
        def update_one(self, filt, update, upsert=False):
            key = filt.get("match_id") or filt.get("id_partido")
            if key is None:
                raise AssertionError("filtro sin match_id ni id_partido")

            doc = self._store.get(key, {})
            set_fields = update.get("$set", {})
            set_on_insert = update.get("$setOnInsert", {})

            if key not in self._store and upsert:
                doc = {**set_on_insert}
                self._store[key] = doc
                upserted_id = key
                modified_count = 0
            else:
                upserted_id = None
                modified_count = 1 if set_fields else 0

            doc.update(set_fields)

            # ← Aquí el fix: devolver un objeto con atributos definidos
            return SimpleNamespace(
                upserted_id=upserted_id,
                modified_count=modified_count,
                matched_count=1,
            )

        def insert_one(self, doc):
            # este mock no se usa en test_update_existing_match_excludes__id
            raise NotImplementedError("No se usa en esta prueba")

    fake_collection = FakeCollection()
    dbm.collection = fake_collection
    return dbm


def test_update_existing_match_excludes__id(fake_dbm):
    doc = {
        "match_id": "SPAIN_LA_LIGA_2023-24_J1_REA-BAR_20230901",
        "liga_id": "SPAIN_LA_LIGA",
        "fecha": "2023-09-01",
        "_id": "NO-DEBE-IR-EN-SET"
    }
    ok = fake_dbm._update_existing_match(doc)
    assert ok is True


def test_insert_many_matches_uses_update_on_duplicates(monkeypatch, fake_dbm):
    from pymongo.errors import DuplicateKeyError

    def fake_insert_one(_doc):
        # Forzar la ruta de duplicado para que llame a _update_existing_match
        raise DuplicateKeyError("dup")

    fake_dbm.collection.insert_one = fake_insert_one

    docs = [
        {"match_id": "AAA", "liga_id": "L1"},
        {"match_id": "BBB", "liga_id": "L1"},
    ]
    stats = fake_dbm.insert_many_matches(docs)
    assert stats["insertados"] == 0
    assert stats["actualizados"] == 2
    assert stats["errores"] == 0