"""Test script for fix.md issues"""

from src.models.entities import ClassificationCategory
from src.models.schemas import ClassificationInput, NormalizationInput
from src.pipeline.classifier import Classifier
from src.pipeline.normalizer import Normalizer
from src.pipeline.atomizer import Atomizer
from src.models.schemas import AtomizationInput


def test_leading_separator():
    """Test: \"; Santos A. L. M.\" should not have leading \"; \""""
    normalizer = Normalizer()
    result = normalizer.normalize(NormalizationInput(original_name="; Santos A. L. M."))

    print("Test 1: Leading separator removal")
    print(f"  Input: '; Santos A. L. M.'")
    print(f"  Normalized: '{result.normalized}'")
    print(f"  Expected: 'SANTOS A.L.M.' (initials normalized)")
    print(f"  PASS" if result.normalized == "SANTOS A.L.M." else f"  FAIL")
    print()
    return result.normalized == "SANTOS A.L.M."


def test_colon_separator_classification():
    """Test: \"Porto De Paula, L. : Ribeiro, I. ; Nogueira, A. C. De O.\" should be CONJUNTO_PESSOAS"""
    classifier = Classifier()
    result = classifier.classify(
        ClassificationInput(text="Porto De Paula, L. : Ribeiro, I. ; Nogueira, A. C. De O.")
    )

    print("Test 2: Colon separator classification")
    print(f"  Input: 'Porto De Paula, L. : Ribeiro, I. ; Nogueira, A. C. De O.'")
    print(f"  Category: {result.category}")
    print(f"  Expected: {ClassificationCategory.CONJUNTO_PESSOAS}")
    print(f"  Patterns matched: {result.patterns_matched}")
    print(f"  PASS" if result.category == ClassificationCategory.CONJUNTO_PESSOAS else f"  FAIL")
    print()
    return result.category == ClassificationCategory.CONJUNTO_PESSOAS


def test_colon_separator_atomization():
    """Test: Atomization should split by colon"""
    atomizer = Atomizer()
    result = atomizer.atomize(
        AtomizationInput(
            text="Porto De Paula, L. : Ribeiro, I. ; Nogueira, A. C. De O.",
            category=ClassificationCategory.CONJUNTO_PESSOAS
        )
    )

    print("Test 3: Colon separator atomization")
    print(f"  Input: 'Porto De Paula, L. : Ribeiro, I. ; Nogueira, A. C. De O.'")
    print(f"  Atomized names ({len(result.atomized_names)}):")
    for name in result.atomized_names:
        print(f"    - '{name.text}' (separator: {name.separator_used})")
    print(f"  Expected: 3 names")
    print(f"  PASS" if len(result.atomized_names) == 3 else f"  FAIL")
    print()
    return len(result.atomized_names) == 3


def test_role_indicator_classification():
    """Test: \"Carlos ( Pai ), LUÍS A. F. (IRMÃO)\" should be CONJUNTO_PESSOAS"""
    classifier = Classifier()
    result = classifier.classify(
        ClassificationInput(text="Carlos ( Pai ), LUÍS A. F. (IRMÃO)")
    )

    print("Test 4: Role indicator classification")
    print(f"  Input: 'Carlos ( Pai ), LUÍS A. F. (IRMÃO)'")
    print(f"  Category: {result.category}")
    print(f"  Expected: {ClassificationCategory.CONJUNTO_PESSOAS}")
    print(f"  Patterns matched: {result.patterns_matched}")
    print(f"  PASS" if result.category == ClassificationCategory.CONJUNTO_PESSOAS else f"  FAIL")
    print()
    return result.category == ClassificationCategory.CONJUNTO_PESSOAS


def test_multiple_commas_classification():
    """Test: \"J. A. A. Meira Neto, M. T Grombone, J. Y, Tamashiro, H. F. Leitão Filho.\" should be CONJUNTO_PESSOAS"""
    classifier = Classifier()
    result = classifier.classify(
        ClassificationInput(text="J. A. A. Meira Neto, M. T Grombone, J. Y, Tamashiro, H. F. Leitão Filho.")
    )

    print("Test 5: Multiple commas classification")
    print(f"  Input: 'J. A. A. Meira Neto, M. T Grombone, J. Y, Tamashiro, H. F. Leitão Filho.'")
    print(f"  Category: {result.category}")
    print(f"  Expected: {ClassificationCategory.CONJUNTO_PESSOAS}")
    print(f"  Patterns matched: {result.patterns_matched}")
    print(f"  PASS" if result.category == ClassificationCategory.CONJUNTO_PESSOAS else f"  FAIL")
    print()
    return result.category == ClassificationCategory.CONJUNTO_PESSOAS


def test_plant_description_filter():
    """Test: \"Flores Verdes\" should be NAO_DETERMINADO"""
    classifier = Classifier()
    result = classifier.classify(
        ClassificationInput(text="Flores Verdes")
    )

    print("Test 6: Plant description filter")
    print(f"  Input: 'Flores Verdes'")
    print(f"  Category: {result.category}")
    print(f"  Expected: {ClassificationCategory.NAO_DETERMINADO}")
    print(f"  Patterns matched: {result.patterns_matched}")
    print(f"  PASS" if result.category == ClassificationCategory.NAO_DETERMINADO else f"  FAIL")
    print()
    return result.category == ClassificationCategory.NAO_DETERMINADO


def test_et_al_atomization():
    """Test: \"Botelho, R. D. ET. AL.\" should extract only \"Botelho, R. D.\""""
    atomizer = Atomizer()
    result = atomizer.atomize(
        AtomizationInput(
            text="Botelho, R. D. ET. AL.",
            category=ClassificationCategory.CONJUNTO_PESSOAS
        )
    )

    print("Test 7: Et al. atomization")
    print(f"  Input: 'Botelho, R. D. ET. AL.'")
    print(f"  Atomized names ({len(result.atomized_names)}):")
    for name in result.atomized_names:
        print(f"    - '{name.text}'")
    print(f"  Expected: 1 name ('Botelho, R. D.')")
    success = (len(result.atomized_names) == 1 and
               result.atomized_names[0].text == "Botelho, R. D.")
    print(f"  PASS" if success else f"  FAIL")
    print()
    return success


def test_canonical_name_format():
    """Test: \"C. FARHAT\" should become \"Farhat, C.\""""
    from src.pipeline.canonicalizer import Canonicalizer
    from src.storage.local_db import LocalDatabase
    from src.models.entities import EntityType
    import tempfile
    import os

    # Create temporary database path
    temp_db_path = tempfile.mktemp(suffix='.db')

    try:
        db = LocalDatabase(temp_db_path)
        canonicalizer = Canonicalizer(db)

        # Test the formatting function directly
        result = canonicalizer._format_canonicalName("C. FARHAT", EntityType.PESSOA)

        print("Test 8: Canonical name format")
        print(f"  Input: 'C. FARHAT'")
        print(f"  Output: '{result}'")
        print(f"  Expected: 'Farhat, C.'")
        print(f"  PASS" if result == "Farhat, C." else f"  FAIL")
        print()

        db.close()
        return result == "Farhat, C."
    finally:
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)


if __name__ == "__main__":
    print("=" * 70)
    print("Testing fixes from docs/fix.md")
    print("=" * 70)
    print()

    results = []
    results.append(test_leading_separator())
    results.append(test_colon_separator_classification())
    results.append(test_colon_separator_atomization())
    results.append(test_role_indicator_classification())
    results.append(test_multiple_commas_classification())
    results.append(test_plant_description_filter())
    results.append(test_et_al_atomization())
    results.append(test_canonical_name_format())

    print("=" * 70)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 70)

    exit(0 if all(results) else 1)
