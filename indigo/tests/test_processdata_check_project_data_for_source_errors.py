from django.test import TestCase  # noqa

import indigo.processdata


class ProcessCheckProjectDataForSourceErrorsData(TestCase):
    def test_none(self):

        input = {"name": {"value": "Project With Ferrets"}}

        (
            source_ids_used_that_are_not_in_sources_table,
            source_table_entries_that_are_not_used,
        ) = indigo.dataqualityreport._check_project_data_for_source_errors(input)

        assert 0 == len(source_ids_used_that_are_not_in_sources_table)
        assert 0 == len(source_table_entries_that_are_not_used)

    def test_one_source_used_fine(self):

        input = {
            "name": {"value": "Project With Ferrets"},
            "intermediary_services": [{"source_ids": "BOOK1"}],
            "sources": [{"id": "BOOK1"}],
        }

        (
            source_ids_used_that_are_not_in_sources_table,
            source_table_entries_that_are_not_used,
        ) = indigo.dataqualityreport._check_project_data_for_source_errors(input)

        assert 0 == len(source_ids_used_that_are_not_in_sources_table)
        assert 0 == len(source_table_entries_that_are_not_used)

    def test_source_not_exist_referenced_in_list(self):

        input = {
            "name": {"value": "Project With Ferrets"},
            "intermediary_services": [{"source_ids": "BOOK1"}],
        }

        (
            source_ids_used_that_are_not_in_sources_table,
            source_table_entries_that_are_not_used,
        ) = indigo.dataqualityreport._check_project_data_for_source_errors(input)

        assert 1 == len(source_ids_used_that_are_not_in_sources_table)
        assert {"source_id": "BOOK1"} == source_ids_used_that_are_not_in_sources_table[
            0
        ]
        assert 0 == len(source_table_entries_that_are_not_used)

    def test_source_not_exist_referenced_in_single_field(self):

        input = {
            "name": {"value": "Project With Ferrets"},
            "dates": {"source_ids": "BOOK1"},
        }

        (
            source_ids_used_that_are_not_in_sources_table,
            source_table_entries_that_are_not_used,
        ) = indigo.dataqualityreport._check_project_data_for_source_errors(input)

        assert 1 == len(source_ids_used_that_are_not_in_sources_table)
        assert {"source_id": "BOOK1"} == source_ids_used_that_are_not_in_sources_table[
            0
        ]
        assert 0 == len(source_table_entries_that_are_not_used)

    def test_source_not_used(self):

        input = {
            "name": {"value": "Project With Ferrets"},
            "sources": [{"id": "Letter1"}],
        }

        (
            source_ids_used_that_are_not_in_sources_table,
            source_table_entries_that_are_not_used,
        ) = indigo.dataqualityreport._check_project_data_for_source_errors(input)

        assert 0 == len(source_ids_used_that_are_not_in_sources_table)
        assert 1 == len(source_table_entries_that_are_not_used)
        assert {"source_id": "Letter1"} == source_table_entries_that_are_not_used[0]

    def test_source_id_wrong(self):

        input = {
            "name": {"value": "Project With Ferrets"},
            "intermediary_services": [{"source_ids": "BOOK1"}],
            "sources": [{"id": "Letter1"}],
        }

        (
            source_ids_used_that_are_not_in_sources_table,
            source_table_entries_that_are_not_used,
        ) = indigo.dataqualityreport._check_project_data_for_source_errors(input)

        assert 1 == len(source_ids_used_that_are_not_in_sources_table)
        assert {"source_id": "BOOK1"} == source_ids_used_that_are_not_in_sources_table[
            0
        ]
        assert 1 == len(source_table_entries_that_are_not_used)
        assert {"source_id": "Letter1"} == source_table_entries_that_are_not_used[0]
