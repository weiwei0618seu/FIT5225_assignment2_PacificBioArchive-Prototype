from __future__ import annotations

from pathlib import Path
import unittest

from pacific_bioarchive.ml.labels import SpeciesLabelMap, normalize_tag


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
LABELS_PATH = REPOSITORY_ROOT / "legacy" / "PacificBioArchive" / "labels.txt"


class SpeciesLabelMapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.labels = SpeciesLabelMap.from_file(LABELS_PATH)

    def test_supplied_labels_match_classifier_output_count(self) -> None:
        self.assertEqual(len(self.labels), 46)
        self.assertEqual(self.labels.class_names[0], "alectura_lathami")
        self.assertEqual(self.labels.class_names[-1], "Uromys_caudimaculatus")

    def test_both_dingo_taxa_share_canonical_tag(self) -> None:
        self.assertEqual(self.labels.resolve("Canis_familiaris").canonical_tag, "dingo")
        self.assertEqual(self.labels.resolve("Canis_dingo").canonical_tag, "dingo")

    def test_blank_common_name_falls_back_to_scientific_name(self) -> None:
        self.assertEqual(self.labels.resolve("Rattus").canonical_tag, "rattus")

    def test_normalize_tag_is_case_and_punctuation_stable(self) -> None:
        self.assertEqual(normalize_tag("  Red-legged_Pademelon!! "), "red legged pademelon")

    def test_unknown_class_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported classifier class"):
            self.labels.resolve("Imaginary_animal")


if __name__ == "__main__":
    unittest.main()

