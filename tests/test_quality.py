"""Testes de regras de negócio e falhas que poderiam invalidar a entrega."""
import copy
import unittest
from datetime import date
from unittest.mock import MagicMock

from etl.model import make_document
from etl.migrate import load_snapshot
from etl.validate import compare_document, metrics, validate


def source_row(receipt=date(1995, 1, 13)):
    return dict(l_orderkey=1, l_linenumber=2, l_shipdate=date(1995, 1, 1),
        l_commitdate=date(1995, 1, 10), l_receiptdate=receipt, l_shipmode="AIR", l_quantity=7,
        l_suppkey=4, fornecedor_nome="Supplier#4", fornecedor_nacao="CANADA", fornecedor_regiao="AMERICA",
        l_partkey=5, p_brand="Brand#11", p_type="TEST", o_custkey=3, cliente_encontrado=3,
        c_mktsegment="BUILDING", cliente_nacao="BRAZIL", cliente_regiao="AMERICA")


def reference_row():
    return {**source_row(), "esperado_atrasada": 1, "esperado_dias": 3, "esperado_mes": "1995-01"}


class QualityTests(unittest.TestCase):
    def test_late_on_time_and_early(self):
        for day, late, days in [(13, True, 3), (10, False, 0), (8, False, 0)]:
            doc = make_document(source_row(date(1995, 1, day)))
            self.assertEqual((doc["entrega"]["atrasada"], doc["entrega"]["diasAtraso"]), (late, days))

    def test_invalid_dates_and_orphans_rejected(self):
        for field, value in [("l_receiptdate", None), ("l_receiptdate", date(1994, 12, 31)),
                             ("fornecedor_nome", None), ("cliente_encontrado", None), ("l_quantity", -1)]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                make_document({**source_row(), field: value})

    def test_mean_is_conditional_and_undefined_without_late_items(self):
        self.assertEqual(metrics({"itens": 4, "atrasados": 2, "dias_atraso": 10})["media_dias_entre_atrasados"], 5)
        self.assertIsNone(metrics({"itens": 4, "atrasados": 0, "dias_atraso": 0})["media_dias_entre_atrasados"])

    def test_dimension_error_detected_despite_identical_measures(self):
        doc = make_document(source_row())
        self.assertEqual(compare_document(reference_row(), doc), [])
        doc["cliente"]["regiao"] = "EUROPE"
        self.assertTrue(any("cliente.regiao" in error for error in compare_document(reference_row(), doc)))

    def test_empty_source_does_not_replace_previous_snapshot(self):
        conn, db = MagicMock(), MagicMock()
        conn.cursor.return_value.__enter__.return_value.fetchone.return_value = {"total": 0}
        with self.assertRaises(ValueError):
            load_snapshot(conn, db, 0, 100)
        db.__getitem__.return_value.rename.assert_not_called()
        db.drop_collection.assert_called_once()

    def test_failed_transformation_does_not_publish_partial_load(self):
        conn, db = MagicMock(), MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = {"total": 1}
        cursor.fetchmany.side_effect = [[{**source_row(), "fornecedor_nome": None}], []]
        with self.assertRaises(ValueError):
            load_snapshot(conn, db, 0, 100)
        db.__getitem__.return_value.rename.assert_not_called()

    def test_success_replaces_snapshot_not_appends(self):
        conn, db = MagicMock(), MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = {"total": 1}
        cursor.fetchmany.side_effect = [[source_row()], []]
        db.__getitem__.return_value.count_documents.return_value = 1
        load_snapshot(conn, db, 1, 100)
        db.__getitem__.return_value.rename.assert_called_once_with("fato_entregas", dropTarget=True)

    def test_empty_validation_fails(self):
        conn, col = MagicMock(), MagicMock()
        conn.cursor.return_value.__enter__.return_value.fetchmany.return_value = []
        col.find.return_value = []
        col.count_documents.return_value = 0
        self.assertEqual(validate(conn, col, 0, 100)["status"], "DIVERGENCIA")

    def test_extra_old_document_fails_validation(self):
        conn, col = MagicMock(), MagicMock()
        conn.cursor.return_value.__enter__.return_value.fetchmany.side_effect = [[reference_row()], []]
        doc = make_document(source_row())
        extra = copy.deepcopy(doc)
        extra["_id"] = "2:1"
        col.find.side_effect = [[doc], [doc, extra]]
        col.count_documents.return_value = 2
        self.assertEqual(validate(conn, col, 1, 100)["status"], "DIVERGENCIA")


if __name__ == "__main__":
    unittest.main()
